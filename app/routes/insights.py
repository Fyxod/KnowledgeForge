import aiofiles
import asyncio
import os
import json
from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.database import db
from core.models.document import Document
from core.studio_features.insights import generate_insights

router = APIRouter(prefix="", tags=["extra"])


class InsightsRequest(BaseModel):
    thread_id: str
    document_id: str


class InsightsGlobalRequest(BaseModel):
    thread_id: str


@router.post("/insights")
async def get_insights(request: Request, body: InsightsRequest = Body(...)):
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

    # Prepare insights file path
    insights_dir = f"data/{user_id}/threads/{thread_id}/insights"
    os.makedirs(insights_dir, exist_ok=True)
    insights_path = os.path.join(insights_dir, f"insights_{document_id}.json")

    # Helper to schedule generation and respond with progress
    async def _generate_and_write():
        try:
            doc = Document.model_validate(document_data)
            result = await generate_insights(doc)
            # Persist the insights output
            async with aiofiles.open(insights_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
                )
        except Exception:
            print("Insights generation failed")
            pass

    # If insights file already exists, inspect its contents
    if os.path.exists(insights_path):
        try:
            async with aiofiles.open(insights_path, "r", encoding="utf-8") as f:
                content = await f.read()
            if not content.strip():
                # File exists but is empty => generation in progress
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Insights for {document_data.get('title', 'Untitled')}",
                    },
                )
            # Non-empty: try to parse and return
            try:
                data = json.loads(content)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status": True, "insights": data},
                )
            except json.JSONDecodeError:
                # Treat invalid JSON as still generating
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Insights for {document_data.get('title', 'Untitled')}",
                    },
                )
        except Exception:
            # On read errors, fall back to treating as generating
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Insights for {document_data.get('title', 'Untitled')}",
                },
            )

    # File does not exist: create it empty (acts as a lock) and kick off generation
    try:
        async with aiofiles.open(insights_path, "w", encoding="utf-8") as f:
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
            "message": f"Generating Insights for {document_data.get('title', 'Untitled')}",
        },
    )


@router.post("/insights/global")
async def insights_global(request: Request, body: InsightsGlobalRequest = Body(...)):
    payload = request.state.user

    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    thread_id = body.thread_id

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

    # Prepare global insights file path
    insights_dir = f"data/{user_id}/threads/{thread_id}/insights"
    os.makedirs(insights_dir, exist_ok=True)
    insights_path = os.path.join(insights_dir, "insights_global.json")

    # Helper to schedule generation and respond with progress
    async def _generate_and_write_global():
        try:
            result = await generate_insights(documents)
            # Persist the insights output
            async with aiofiles.open(insights_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
                )
        except Exception as e:
            print("Global insights generation failed:", e)
            pass

    # If insights file already exists, inspect its contents
    if os.path.exists(insights_path):
        try:
            async with aiofiles.open(insights_path, "r", encoding="utf-8") as f:
                content = await f.read()
            if not content.strip():
                # File exists but is empty => generation in progress
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Global Insights for thread {thread_id}",
                    },
                )
            # Non-empty: try to parse and return
            try:
                data = json.loads(content)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status": True, "insights": data},
                )
            except json.JSONDecodeError:
                # Treat invalid JSON as still generating
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Global Insights for thread {thread_id}",
                    },
                )
        except Exception:
            # On read errors, fall back to treating as generating
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Global Insights for thread {thread_id}",
                },
            )

    # File does not exist: create it empty (acts as a lock) and kick off generation
    try:
        async with aiofiles.open(insights_path, "w", encoding="utf-8") as f:
            await f.write("")
    except Exception:
        # If file creation fails, still proceed to schedule generation
        pass

    # Schedule background generation without blocking the response
    asyncio.create_task(_generate_and_write_global())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": False,
            "message": f"Generating Global Insights for thread {thread_id}",
        },
    )
