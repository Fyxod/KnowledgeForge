"""
Tech Sensing API — on-demand tech sensing report generation.

Endpoints:
  POST   /sensing/generate              — kick off async report generation
  GET    /sensing/status/{tracking_id}  — poll for completion
  GET    /sensing/history               — list past reports
  DELETE /sensing/report/{report_id}    — delete a report
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
                    }
                )
            except Exception:
                continue

    reports.sort(key=lambda r: r.get("generated_at", ""), reverse=True)
    return JSONResponse(content={"reports": reports})


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
