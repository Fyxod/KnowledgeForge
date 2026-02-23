import aiofiles
import asyncio
import os
import json
import traceback
from fastapi import APIRouter, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.database import db
from core.models.document import Document
from core.studio_features.technical_analysis import generate_technical_analysis

router = APIRouter(prefix="", tags=["extra"])


class TechnicalAnalysisRequest(BaseModel):
    thread_id: str
    document_id: str
    regenerate: bool = False


class TechnicalAnalysisGlobalRequest(BaseModel):
    thread_id: str
    regenerate: bool = False


@router.post("/technical_analysis")
async def get_technical_analysis(
    request: Request, body: TechnicalAnalysisRequest = Body(...)
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

    # Prepare technical analysis file path
    analysis_dir = f"data/{user_id}/threads/{thread_id}/technical_analyses"
    os.makedirs(analysis_dir, exist_ok=True)
    analysis_path = os.path.join(
        analysis_dir, f"technical_analysis_{document_id}.json"
    )

    # Helper to schedule generation and respond with progress
    async def _generate_and_write():
        try:
            doc = Document.model_validate(document_data)
            result = await generate_technical_analysis(doc)
            # Persist the technical analysis output
            async with aiofiles.open(analysis_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
                )
        except Exception:
            # Clean up the lock file so the next poll triggers a retry
            if os.path.exists(analysis_path):
                try:
                    os.remove(analysis_path)
                except Exception:
                    pass
            error_details = traceback.format_exc()
            try:
                with open(
                    os.path.join(analysis_dir, "error.txt"), "w"
                ) as ef:
                    ef.write(
                        f"Error in _generate_and_write: {error_details}"
                    )
            except Exception:
                pass
            print(f"Error generating technical analysis: {error_details}")

    # If regenerating, remove existing file so a fresh generation is triggered
    if regenerate and os.path.exists(analysis_path):
        os.remove(analysis_path)

    # If analysis file already exists, inspect its contents
    if os.path.exists(analysis_path):
        try:
            async with aiofiles.open(analysis_path, "r", encoding="utf-8") as f:
                content = await f.read()
            if not content.strip():
                # File exists but is empty => generation in progress
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Technical Analysis for {document_data.get('title', 'Untitled')}",
                    },
                )
            # Non-empty: try to parse and return
            try:
                data = json.loads(content)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status": True, "technical_analysis": data},
                )
            except json.JSONDecodeError:
                # Treat invalid JSON as still generating
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Technical Analysis for {document_data.get('title', 'Untitled')}",
                    },
                )
        except Exception:
            # On read errors, fall back to treating as generating
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Technical Analysis for {document_data.get('title', 'Untitled')}",
                },
            )

    # File does not exist: create it empty (acts as a lock) and kick off generation
    try:
        async with aiofiles.open(analysis_path, "w", encoding="utf-8") as f:
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
            "message": f"Generating Technical Analysis for {document_data.get('title', 'Untitled')}",
        },
    )


@router.post("/technical_analysis/global")
async def technical_analysis_global(
    request: Request, body: TechnicalAnalysisGlobalRequest = Body(...)
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
                            print(
                                f"Skipping invalid document in technical analysis global: {file_path}"
                            )
                            continue
                except Exception:
                    continue

    if not documents:
        raise HTTPException(
            status_code=404, detail="No documents found for thread"
        )

    # Prepare global technical analysis file path
    analysis_dir = f"data/{user_id}/threads/{thread_id}/technical_analyses"
    os.makedirs(analysis_dir, exist_ok=True)
    analysis_path = os.path.join(analysis_dir, "technical_analysis_global.json")

    async def _generate_and_write_global():
        try:
            result = await generate_technical_analysis(documents)
            async with aiofiles.open(analysis_path, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
                )
        except Exception:
            # Clean up lock file to allow retry
            if os.path.exists(analysis_path):
                try:
                    os.remove(analysis_path)
                except Exception:
                    pass
            error_details = traceback.format_exc()
            try:
                with open(
                    os.path.join(analysis_dir, "error_global.txt"), "w"
                ) as ef:
                    ef.write(
                        f"Error in _generate_and_write_global: {error_details}"
                    )
            except Exception:
                pass
            print(
                f"Error generating global technical analysis: {error_details}"
            )

    if regenerate and os.path.exists(analysis_path):
        os.remove(analysis_path)

    # If analysis file already exists, inspect its contents
    if os.path.exists(analysis_path):
        try:
            async with aiofiles.open(analysis_path, "r", encoding="utf-8") as f:
                content = await f.read()
            if not content.strip():
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Global Technical Analysis for thread {thread_id}",
                    },
                )
            try:
                data = json.loads(content)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status": True, "technical_analysis": data},
                )
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": False,
                        "message": f"Generating Global Technical Analysis for thread {thread_id}",
                    },
                )
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": False,
                    "message": f"Generating Global Technical Analysis for thread {thread_id}",
                },
            )

    # File does not exist: create it empty (acts as a lock) and kick off generation
    try:
        async with aiofiles.open(analysis_path, "w", encoding="utf-8") as f:
            await f.write("")
    except Exception:
        pass

    asyncio.create_task(_generate_and_write_global())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": False,
            "message": f"Generating Global Technical Analysis for thread {thread_id}",
        },
    )
