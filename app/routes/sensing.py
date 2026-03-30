"""
Tech Sensing API — on-demand tech sensing report generation.

Endpoints:
  POST   /sensing/generate              — kick off async report generation
  GET    /sensing/status/{tracking_id}  — poll for completion
  GET    /sensing/history               — list past reports
  DELETE /sensing/report/{report_id}    — delete a report
  GET    /sensing/compare               — compare two reports
"""

import asyncio
import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.socket_handler import sio
from core.utils.generation_status import (
    read_generation_status,
    write_failed_status,
    write_pending_status,
    write_result,
)

# Sensing pipeline can take 10-15 min (RSS + DDG + LLM classify + LLM report).
# Override the global 8-min stale timeout for sensing status reads.
SENSING_STALE_TIMEOUT_MINUTES = 60

router = APIRouter(prefix="/sensing", tags=["Tech Sensing"])


# --- Request/Response Models ---


class SensingGenerateRequest(BaseModel):
    domain: str = Field(default="Generative AI", description="Target domain / topic")
    custom_requirements: str = Field(
        default="",
        description="Additional user guidance for the report",
    )
    must_include: Optional[List[str]] = Field(
        default=None,
        description="Keywords to prioritize in article discovery and classification",
    )
    dont_include: Optional[List[str]] = Field(
        default=None,
        description="Keywords to exclude from article discovery and classification",
    )
    lookback_days: int = Field(
        default=7,
        description="Number of days to look back (7=last week, 30=last month)",
    )
    feed_urls: Optional[List[str]] = Field(
        default=None,
        description="Override default RSS feed URLs",
    )
    search_queries: Optional[List[str]] = Field(
        default=None,
        description="Override default search queries",
    )


# --- Helpers ---


def _get_sensing_dir(user_id: str) -> str:
    """Storage path: data/{user_id}/sensing/"""
    return f"data/{user_id}/sensing"


# --- Generate ---


@router.post("/generate")
async def generate_sensing_report(
    request: Request,
    body: SensingGenerateRequest = Body(...),
):
    """Start async tech sensing report generation."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    tracking_id = str(uuid.uuid4())
    sensing_dir = _get_sensing_dir(user_id)
    os.makedirs(sensing_dir, exist_ok=True)
    status_path = os.path.join(sensing_dir, f"status_{tracking_id}.json")
    await write_pending_status(status_path)

    async def _run():
        try:
            from core.sensing.pipeline import run_sensing_pipeline

            async def _progress_cb(stage, pct, msg):
                await sio.emit(
                    f"{user_id}/sensing_progress",
                    {
                        "tracking_id": tracking_id,
                        "stage": stage,
                        "progress": pct,
                        "message": msg,
                    },
                )

            result = await run_sensing_pipeline(
                domain=body.domain,
                custom_requirements=body.custom_requirements,
                feed_urls=body.feed_urls,
                search_queries=body.search_queries,
                must_include=body.must_include,
                dont_include=body.dont_include,
                lookback_days=body.lookback_days,
                progress_callback=_progress_cb,
                user_id=user_id,
            )

            report_data = {
                "report": result.report.model_dump(),
                "meta": {
                    "tracking_id": tracking_id,
                    "domain": body.domain,
                    "raw_article_count": result.raw_article_count,
                    "deduped_article_count": result.deduped_article_count,
                    "classified_article_count": result.classified_article_count,
                    "execution_time_seconds": result.execution_time_seconds,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    # Preserve generation params for regeneration
                    "custom_requirements": body.custom_requirements,
                    "must_include": body.must_include,
                    "dont_include": body.dont_include,
                    "lookback_days": body.lookback_days,
                },
            }

            await write_result(status_path, report_data)

            # Also save a persistent copy
            report_path = os.path.join(
                sensing_dir, f"report_{tracking_id}.json"
            )
            async with aiofiles.open(report_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(report_data, ensure_ascii=False, indent=2)
                )

            await sio.emit(
                f"{user_id}/sensing_progress",
                {
                    "tracking_id": tracking_id,
                    "stage": "complete",
                    "progress": 100,
                    "message": "Report ready",
                },
            )

        except Exception:
            error_details = traceback.format_exc()
            await write_failed_status(status_path, error_details)
            print(f"[Sensing:route] Generation failed: {error_details}")
            await sio.emit(
                f"{user_id}/sensing_progress",
                {
                    "tracking_id": tracking_id,
                    "stage": "error",
                    "progress": 0,
                    "message": "Report generation failed",
                },
            )

    asyncio.create_task(_run())

    return JSONResponse(
        content={
            "status": "pending",
            "tracking_id": tracking_id,
            "message": f"Generating Tech Sensing Report for '{body.domain}'",
        }
    )


# --- Status ---


@router.get("/status/{tracking_id}")
async def sensing_status(request: Request, tracking_id: str):
    """Poll for report generation status (with extended timeout for sensing)."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    status_path = os.path.join(
        _get_sensing_dir(user_id), f"status_{tracking_id}.json"
    )

    gen_status = await _read_sensing_status(status_path)
    if gen_status is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if gen_status["state"] == "pending":
        return JSONResponse(content={"status": "pending"})
    elif gen_status["state"] == "failed":
        return JSONResponse(
            content={"status": "failed", "error": gen_status.get("error", "")}
        )
    else:  # completed
        return JSONResponse(
            content={"status": "completed", "data": gen_status["data"]}
        )


async def _read_sensing_status(file_path: str) -> dict | None:
    """
    Custom status reader for sensing with a longer stale timeout (20 min).
    The global read_generation_status uses 8 min which is too short for
    the sensing pipeline (RSS + DDG + LLM classify batches + LLM report).
    """
    if not os.path.exists(file_path):
        return None

    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()
    except Exception:
        return None

    if not content.strip():
        return {
            "state": "failed",
            "error": "Generation failed (empty status file). Please retry.",
        }

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"state": "failed", "error": "Corrupted status file. Please retry."}

    if not isinstance(data, dict):
        return {"state": "failed", "error": "Unexpected status file format."}

    status_field = data.get("_status")

    if status_field == "pending":
        started_at = data.get("started_at")
        if started_at:
            try:
                started = datetime.fromisoformat(started_at)
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                if elapsed > SENSING_STALE_TIMEOUT_MINUTES * 60:
                    return {
                        "state": "failed",
                        "error": (
                            f"Generation timed out (no result after "
                            f"{SENSING_STALE_TIMEOUT_MINUTES} minutes). "
                            f"Please retry."
                        ),
                    }
            except (ValueError, TypeError):
                pass
        return {"state": "pending"}

    if status_field == "failed":
        return {"state": "failed", "error": data.get("error", "Unknown error")}

    # Completed (no _status key)
    return {"state": "completed", "data": data}


# --- History ---


@router.get("/history")
async def sensing_history(request: Request):
    """List past sensing reports for the current user."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    sensing_dir = _get_sensing_dir(user_id)

    if not os.path.exists(sensing_dir):
        return JSONResponse(content={"reports": []})

    reports = []
    for fname in os.listdir(sensing_dir):
        if fname.startswith("report_") and fname.endswith(".json"):
            try:
                fpath = os.path.join(sensing_dir, fname)
                async with aiofiles.open(fpath, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                meta = data.get("meta", {})
                report = data.get("report", {})
                reports.append(
                    {
                        "tracking_id": meta.get("tracking_id"),
                        "domain": meta.get("domain"),
                        "generated_at": meta.get("generated_at"),
                        "report_title": report.get("report_title", "Untitled"),
                        "total_articles": report.get(
                            "total_articles_analyzed", 0
                        ),
                        # Generation params for regeneration
                        "custom_requirements": meta.get("custom_requirements", ""),
                        "must_include": meta.get("must_include"),
                        "dont_include": meta.get("dont_include"),
                        "lookback_days": meta.get("lookback_days", 7),
                    }
                )
            except Exception:
                continue

    reports.sort(key=lambda r: r.get("generated_at", ""), reverse=True)
    return JSONResponse(content={"reports": reports})


# --- Feeds ---


@router.get("/feeds")
async def sensing_feeds(request: Request, domain: str = "Generative AI"):
    """Return default RSS feeds and search queries for a domain."""
    from core.sensing.config import get_feeds_for_domain, get_search_queries_for_domain

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    feeds = get_feeds_for_domain(domain)
    queries = get_search_queries_for_domain(domain)
    return JSONResponse(content={"feeds": feeds, "queries": queries})


# --- Compare ---


@router.get("/compare")
async def sensing_compare(request: Request, a: str, b: str):
    """Compare two sensing reports by tracking ID."""
    from core.sensing.comparison import compare_reports

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    sensing_dir = _get_sensing_dir(user_id)

    async def _load(tid: str) -> dict:
        fpath = os.path.join(sensing_dir, f"report_{tid}.json")
        if not os.path.exists(fpath):
            raise HTTPException(status_code=404, detail=f"Report {tid} not found")
        async with aiofiles.open(fpath, "r", encoding="utf-8") as f:
            return json.loads(await f.read())

    report_a = await _load(a)
    report_b = await _load(b)
    comparison = compare_reports(report_a, report_b)
    return JSONResponse(content=comparison.model_dump())


# --- Delete ---


@router.delete("/report/{report_id}")
async def delete_sensing_report(request: Request, report_id: str):
    """Delete a sensing report."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    sensing_dir = _get_sensing_dir(user_id)

    for prefix in ("report_", "status_"):
        fpath = os.path.join(sensing_dir, f"{prefix}{report_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)

    return JSONResponse(content={"status": "deleted"})


# --- Schedules ---


class SensingScheduleRequest(BaseModel):
    domain: str = Field(default="Generative AI")
    frequency: str = Field(default="weekly", description="weekly|biweekly|monthly|daily")
    custom_requirements: str = Field(default="")
    must_include: Optional[List[str]] = None
    dont_include: Optional[List[str]] = None
    lookback_days: int = Field(default=7)


@router.post("/schedule")
async def create_schedule(request: Request, body: SensingScheduleRequest = Body(...)):
    """Create a new sensing report schedule."""
    from core.sensing.scheduler import add_schedule

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    schedule = await add_schedule({
        "user_id": payload.userId,
        "domain": body.domain,
        "frequency": body.frequency,
        "custom_requirements": body.custom_requirements,
        "must_include": body.must_include,
        "dont_include": body.dont_include,
        "lookback_days": body.lookback_days,
    })
    return JSONResponse(content=schedule)


@router.get("/schedules")
async def get_schedules(request: Request):
    """List user's sensing schedules."""
    from core.sensing.scheduler import list_schedules

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    schedules = await list_schedules(payload.userId)
    return JSONResponse(content={"schedules": schedules})


@router.put("/schedule/{schedule_id}")
async def update_schedule_endpoint(
    request: Request, schedule_id: str, body: dict = Body(...)
):
    """Update a schedule (enable/disable, change frequency, etc.)."""
    from core.sensing.scheduler import update_schedule

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    updated = await update_schedule(schedule_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return JSONResponse(content=updated)


@router.delete("/schedule/{schedule_id}")
async def delete_schedule(request: Request, schedule_id: str):
    """Delete a sensing schedule."""
    from core.sensing.scheduler import remove_schedule

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    removed = await remove_schedule(schedule_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return JSONResponse(content={"status": "deleted"})


# --- Timeline ---


@router.get("/timeline")
async def sensing_timeline(request: Request, domain: str = ""):
    """Build multi-report timeline for a domain."""
    from core.sensing.timeline import build_timeline

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    timeline = await build_timeline(
        user_id=payload.userId,
        domain=domain if domain else None,
    )
    return JSONResponse(content=timeline.model_dump())


# --- Org Context ---


class OrgContextRequest(BaseModel):
    tech_stack: List[str] = []
    industry: str = ""
    priorities: List[str] = []


@router.get("/org-context")
async def get_org_context(request: Request):
    """Get user's org tech context."""
    from core.sensing.org_context import load_org_context

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    context = await load_org_context(payload.userId)
    if not context:
        return JSONResponse(content={"tech_stack": [], "industry": "", "priorities": []})
    return JSONResponse(content=context.model_dump())


@router.put("/org-context")
async def update_org_context(
    request: Request, body: OrgContextRequest = Body(...)
):
    """Update user's org tech context."""
    from core.sensing.org_context import OrgTechContext, save_org_context

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    context = OrgTechContext(
        tech_stack=body.tech_stack,
        industry=body.industry,
        priorities=body.priorities,
    )
    await save_org_context(payload.userId, context)
    return JSONResponse(content=context.model_dump())


# --- Deep Dive ---


class DeepDiveRequest(BaseModel):
    technology_name: str
    domain: str = Field(default="Generative AI")


@router.post("/deep-dive")
async def start_deep_dive(
    request: Request,
    body: DeepDiveRequest = Body(...),
):
    """Start async deep dive analysis on a technology."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    tracking_id = str(uuid.uuid4())
    sensing_dir = _get_sensing_dir(user_id)
    os.makedirs(sensing_dir, exist_ok=True)
    status_path = os.path.join(sensing_dir, f"deepdive_status_{tracking_id}.json")
    await write_pending_status(status_path)

    async def _run():
        try:
            from core.sensing.deep_dive import run_deep_dive

            async def _progress_cb(stage, pct, msg):
                await sio.emit(
                    f"{user_id}/sensing_progress",
                    {
                        "tracking_id": tracking_id,
                        "stage": stage,
                        "progress": pct,
                        "message": msg,
                    },
                )

            result = await run_deep_dive(
                technology_name=body.technology_name,
                domain=body.domain,
                user_id=user_id,
                progress_callback=_progress_cb,
            )

            report_data = result.model_dump()
            await write_result(status_path, report_data)

            # Save persistent copy
            report_path = os.path.join(
                sensing_dir, f"deepdive_{tracking_id}.json"
            )
            async with aiofiles.open(report_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(report_data, ensure_ascii=False, indent=2)
                )

            await sio.emit(
                f"{user_id}/sensing_progress",
                {
                    "tracking_id": tracking_id,
                    "stage": "complete",
                    "progress": 100,
                    "message": "Deep dive ready",
                },
            )

        except Exception:
            error_details = traceback.format_exc()
            await write_failed_status(status_path, error_details)
            await sio.emit(
                f"{user_id}/sensing_progress",
                {
                    "tracking_id": tracking_id,
                    "stage": "error",
                    "progress": 0,
                    "message": "Deep dive failed",
                },
            )

    asyncio.create_task(_run())

    return JSONResponse(
        content={
            "status": "pending",
            "tracking_id": tracking_id,
            "message": f"Deep dive starting for '{body.technology_name}'",
        }
    )


@router.get("/deep-dive/status/{tracking_id}")
async def deep_dive_status(request: Request, tracking_id: str):
    """Poll for deep dive status."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    status_path = os.path.join(
        _get_sensing_dir(user_id), f"deepdive_status_{tracking_id}.json"
    )

    gen_status = await _read_sensing_status(status_path)
    if gen_status is None:
        raise HTTPException(status_code=404, detail="Deep dive not found")

    if gen_status["state"] == "pending":
        return JSONResponse(content={"status": "pending"})
    elif gen_status["state"] == "failed":
        return JSONResponse(
            content={"status": "failed", "error": gen_status.get("error", "")}
        )
    else:
        return JSONResponse(
            content={"status": "completed", "data": gen_status["data"]}
        )


# --- Collaboration ---


class VoteRequest(BaseModel):
    radar_item_name: str
    suggested_ring: str
    reasoning: str = ""


class CommentRequest(BaseModel):
    text: str
    radar_item_name: str = ""


@router.post("/share/{report_id}")
async def share_report(request: Request, report_id: str):
    """Create a shared report link."""
    from core.sensing.collaboration import create_shared_report

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    shared = await create_shared_report(
        report_tracking_id=report_id,
        owner_user_id=payload.userId,
    )
    return JSONResponse(content=shared.model_dump())


@router.get("/shared/{share_id}")
async def get_shared_report(request: Request, share_id: str):
    """Load a shared report (with the underlying report data)."""
    from core.sensing.collaboration import load_shared_report

    shared = await load_shared_report(share_id)
    if not shared:
        raise HTTPException(status_code=404, detail="Shared report not found")

    # Load the actual report data
    user_id = shared.owner_user_id
    sensing_dir = _get_sensing_dir(user_id)
    report_path = os.path.join(
        sensing_dir, f"report_{shared.report_tracking_id}.json"
    )

    report_data = None
    if os.path.exists(report_path):
        try:
            async with aiofiles.open(report_path, "r", encoding="utf-8") as f:
                report_data = json.loads(await f.read())
        except Exception:
            pass

    return JSONResponse(
        content={
            "shared": shared.model_dump(),
            "report": report_data,
        }
    )


@router.post("/shared/{share_id}/vote")
async def vote_on_shared(
    request: Request,
    share_id: str,
    body: VoteRequest = Body(...),
):
    """Add a ring vote to a shared report."""
    from core.sensing.collaboration import add_vote

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    vote = await add_vote(
        share_id=share_id,
        user_id=payload.userId,
        user_name=getattr(payload, 'name', payload.userId),
        radar_item_name=body.radar_item_name,
        suggested_ring=body.suggested_ring,
        reasoning=body.reasoning,
    )
    if not vote:
        raise HTTPException(status_code=404, detail="Shared report not found")
    return JSONResponse(content=vote.model_dump())


@router.post("/shared/{share_id}/comment")
async def comment_on_shared(
    request: Request,
    share_id: str,
    body: CommentRequest = Body(...),
):
    """Add a comment to a shared report."""
    from core.sensing.collaboration import add_comment

    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    comment = await add_comment(
        share_id=share_id,
        user_id=payload.userId,
        user_name=getattr(payload, 'name', payload.userId),
        text=body.text,
        radar_item_name=body.radar_item_name,
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Shared report not found")
    return JSONResponse(content=comment.model_dump())


@router.get("/shared/{share_id}/feedback")
async def get_shared_feedback(request: Request, share_id: str):
    """Get all votes and comments for a shared report."""
    from core.sensing.collaboration import get_feedback

    feedback = await get_feedback(share_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Shared report not found")
    return JSONResponse(content=feedback)
