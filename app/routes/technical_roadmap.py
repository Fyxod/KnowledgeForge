import asyncio
import json
import os

import aiofiles
from fastapi import APIRouter, Body, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.database import db
from core.models.document import Document
from core.studio_features.technical_roadmap import generate_technical_roadmap
from core.utils.generation_status import (
    write_pending_status,
    write_failed_status,
    write_result,
    read_generation_status,
)

router = APIRouter(prefix="", tags=["extra"])


class TechnicalRoadmapRequest(BaseModel):
    thread_id: str
    document_id: str
    regenerate: bool = False


class TechnicalRoadmapGlobalRequest(BaseModel):
    thread_id: str
    regenerate: bool = False


@router.post("/technical_roadmap")
async def get_technical_roadmap(
    request: Request, body: TechnicalRoadmapRequest = Body(...)
):
    payload = request.state.user

    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    thread_id = body.thread_id
    document_id = body.document_id
    regenerate = body.regenerate

    user_id = payload.userId
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    thread = user["threads"].get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Locate the parsed document to retrieve metadata (e.g., title)
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    document_data = None
    if os.path.exists(parsed_dir):
        for filename in os.listdir(parsed_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(parsed_dir, filename)
                try:
                    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                        content = await f.read()
                    data = json.loads(content)
                    if isinstance(data, dict) and data.get("id") == document_id:
                        document_data = data
                        break
                except Exception:
                    continue

    if document_data is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prepare technical roadmap file path
    roadmap_dir = f"data/{user_id}/threads/{thread_id}/technical_roadmaps"
    os.makedirs(roadmap_dir, exist_ok=True)
    roadmap_path = os.path.join(roadmap_dir, f"technical_roadmap_{document_id}.json")

    # Helper to schedule generation and respond with progress
    async def _generate_and_write():
        try:
            doc = Document.model_validate(document_data)
            result = await generate_technical_roadmap(doc)
            # Persist the technical roadmap output
            await write_result(roadmap_path, result.model_dump())
        except Exception as e:
            await write_failed_status(roadmap_path, str(e))
            print(f"Error generating technical roadmap: {e}")

    # If regenerating, remove existing file so a fresh generation is triggered
    if regenerate and os.path.exists(roadmap_path):
        os.remove(roadmap_path)

    # If roadmap file already exists, inspect its status
    if os.path.exists(roadmap_path):
        gen_status = await read_generation_status(roadmap_path)
        if gen_status is None:
            pass  # fall through to create pending
        elif gen_status["state"] == "pending":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Technical Roadmap for {document_data.get('title', 'Untitled')}",
                },
            )
        elif gen_status["state"] == "failed":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "error": gen_status["error"],
                    "failed": True,
                },
            )
        elif gen_status["state"] == "completed":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": True, "technical_roadmap": gen_status["data"]},
            )

    # Write pending status and kick off generation
    await write_pending_status(roadmap_path)

    # Schedule background generation without blocking the response
    asyncio.create_task(_generate_and_write())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": False,
            "message": f"Generating Technical Roadmap for {document_data.get('title', 'Untitled')}",
        },
    )


@router.post("/technical_roadmap/global")
async def technical_roadmap_global(
    request: Request, body: TechnicalRoadmapGlobalRequest = Body(...)
):
    payload = request.state.user

    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    thread_id = body.thread_id
    regenerate = body.regenerate

    user_id = payload.userId
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    thread = user["threads"].get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Load all parsed documents for this thread
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    documents: list[Document] = []
    if os.path.exists(parsed_dir):
        for filename in os.listdir(parsed_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(parsed_dir, filename)
                try:
                    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                        content = await f.read()
                    data = json.loads(content)
                    if isinstance(data, dict):
                        try:
                            documents.append(Document.model_validate(data))
                        except Exception:
                            continue
                except Exception:
                    continue

    if not documents:
        raise HTTPException(status_code=404, detail="No documents found for thread")

    # Prepare global technical roadmap file path
    roadmap_dir = f"data/{user_id}/threads/{thread_id}/technical_roadmaps"
    os.makedirs(roadmap_dir, exist_ok=True)
    roadmap_path = os.path.join(roadmap_dir, "technical_roadmap_global.json")

    async def _generate_and_write_global():
        try:
            # Pass a list[Document] to the generator
            result = await generate_technical_roadmap(documents)
            await write_result(roadmap_path, result.model_dump())
        except Exception as e:
            await write_failed_status(roadmap_path, str(e))
            print(f"Error generating global technical roadmap: {e}")

    # If regenerating, remove existing file so a fresh generation is triggered
    if regenerate and os.path.exists(roadmap_path):
        os.remove(roadmap_path)

    # If roadmap file already exists, inspect its status
    if os.path.exists(roadmap_path):
        gen_status = await read_generation_status(roadmap_path)
        if gen_status is None:
            pass  # fall through to create pending
        elif gen_status["state"] == "pending":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Global Technical Roadmap for thread {thread_id}",
                },
            )
        elif gen_status["state"] == "failed":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "error": gen_status["error"],
                    "failed": True,
                },
            )
        elif gen_status["state"] == "completed":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": True, "technical_roadmap": gen_status["data"]},
            )

    # Write pending status and kick off generation
    await write_pending_status(roadmap_path)

    # Schedule background generation without blocking the response
    asyncio.create_task(_generate_and_write_global())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": False,
            "message": f"Generating Global Technical Roadmap for thread {thread_id}",
        },
    )
