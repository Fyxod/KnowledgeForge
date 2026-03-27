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

router = APIRouter(prefix="/sensing", tags=["Tech Sensing"])


# --- Request/Response Models ---


class SensingGenerateRequest(BaseModel):
    domain: str = Field(default="Generative AI", description="Target domain")
    custom_requirements: str = Field(
        default="",
        description="Additional user guidance for the report",
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
    """Poll for report generation status."""
    payload = request.state.user
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = payload.userId
    status_path = os.path.join(
        _get_sensing_dir(user_id), f"status_{tracking_id}.json"
    )

    gen_status = await read_generation_status(status_path)
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
