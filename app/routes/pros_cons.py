import aiofiles
import asyncio
import os
import json
from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.database import db
from core.models.document import Document
from core.pros_cons import generate_pros_cons
from app.socket_handler import sio

router = APIRouter(prefix="", tags=["extra"])


class ProsConsRequest(BaseModel):
    thread_id: str
    document_id: str


@router.post("/pros_cons")
async def get_pros_cons(request: Request, body: ProsConsRequest = Body(...)):
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

    # Prepare pros_cons file path
    pros_cons_dir = f"data/{user_id}/threads/{thread_id}/pros_cons"
    os.makedirs(pros_cons_dir, exist_ok=True)
    pros_cons_path = os.path.join(pros_cons_dir, f"pros_cons_{document_id}.json")

    # Helper to schedule generation and respond with progress
    async def _generate_and_write():
        try:
            doc = Document.model_validate(document_data)
            result = await generate_pros_cons(doc)
            # Persist the pros_cons output
            async with aiofiles.open(pros_cons_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
                )
        except Exception:
            # Silently ignore to avoid crashing the request path; a retry can be triggered by client
            pass

    # If file already exists, inspect its contents
    if os.path.exists(pros_cons_path):
        try:
            async with aiofiles.open(pros_cons_path, "r", encoding="utf-8") as f:
                content = await f.read()
            if not content.strip():
                # File exists but is empty => generation in progress
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Pros & Cons for {document_data.get('title', 'Untitled')}",
                    },
                )
            # Non-empty: try to parse and return
            try:
                data = json.loads(content)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status": True, "pros_cons": data},
                )
            except json.JSONDecodeError:
                # Treat invalid JSON as still generating
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Pros & Cons for {document_data.get('title', 'Untitled')}",
                    },
                )
        except Exception:
            # On read errors, fall back to treating as generating
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Pros & Cons for {document_data.get('title', 'Untitled')}",
                },
            )

    # File does not exist: create it empty (acts as a lock) and kick off generation
    try:
        async with aiofiles.open(pros_cons_path, "w", encoding="utf-8") as f:
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
            "message": f"Generating Pros & Cons for {document_data.get('title', 'Untitled')}",
        },
    )
