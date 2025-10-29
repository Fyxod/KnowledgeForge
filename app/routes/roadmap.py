import aiofiles
import asyncio
import os
import json
from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.database import db
from core.models.document import Document
from core.roadmap import generate_roadmap
from app.socket_handler import sio

router = APIRouter(prefix="", tags=["extra"])


class RoadmapRequest(BaseModel):
    thread_id: str
    document_id: str


@router.post("/roadmap")
async def get_roadmap(request: Request, body: RoadmapRequest = Body(...)):
    payload = request.state.user

    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    thread_id = body.thread_id
    document_id = body.document_id

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

    # Prepare roadmap file path
    roadmap_dir = f"data/{user_id}/threads/{thread_id}/roadmaps"
    os.makedirs(roadmap_dir, exist_ok=True)
    roadmap_path = os.path.join(roadmap_dir, f"roadmap_{document_id}.json")

    # Helper to schedule generation and respond with progress
    async def _generate_and_write():
        try:
            # Build Document model from parsed data
            # doc = Document(
            #     id=document_data.get("id", document_id),
            #     type=document_data.get("type", "unknown"),
            #     file_name=document_data.get("file_name", "document"),
            #     title=document_data.get("title", "Untitled"),
            #     full_text=document_data.get("full_text", ""),
            #     summary=document_data.get("summary"),
            # )

            doc = Document.model_validate(document_data)
            result = await generate_roadmap(doc)
            # Persist the roadmap output
            async with aiofiles.open(roadmap_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
                )
        except Exception:
            # Silently ignore to avoid crashing the request path; a retry can be triggered by client
            pass

    # If roadmap file already exists, inspect its contents
    if os.path.exists(roadmap_path):
        try:
            async with aiofiles.open(roadmap_path, "r", encoding="utf-8") as f:
                content = await f.read()
            if not content.strip():
                # File exists but is empty => generation in progress
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Roadmap for {document_data.get('title', 'Untitled')}",
                    },
                )
            # Non-empty: try to parse and return
            try:
                data = json.loads(content)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status": True, "roadmap": data},
                )
            except json.JSONDecodeError:
                # Treat invalid JSON as still generating
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Roadmap for {document_data.get('title', 'Untitled')}",
                    },
                )
        except Exception:
            # On read errors, fall back to treating as generating
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Roadmap for {document_data.get('title', 'Untitled')}",
                },
            )

    # File does not exist: create it empty (acts as a lock) and kick off generation
    try:
        async with aiofiles.open(roadmap_path, "w", encoding="utf-8") as f:
            await f.write("")
    except Exception:
        # If file creation fails, still proceed to schedule generation
        pass

    # Schedule background generation without blocking the response
    asyncio.create_task(_generate_and_write())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": False,
            "message": f"Generating Roadmap for {document_data.get('title', 'Untitled')}",
        },
    )
