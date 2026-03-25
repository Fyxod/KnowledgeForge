import asyncio
import json
import os

import aiofiles
from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel

from core.database import db
from core.studio_features.word_cloud import generate_word_cloud
from core.utils.generation_status import (
    write_pending_status,
    read_generation_status,
)

router = APIRouter(prefix="", tags=["extra"])


class WordCloudRequest(BaseModel):
    document_ids: list[str]
    max_words: int | None = None


class MindMapRequest(BaseModel):
    thread_id: str
    document_id: str
    regenerate: bool = False


class GlobalSummaryRequest(BaseModel):
    thread_id: str
    regenerate: bool = False


@router.post("/wordcloud/{thread_id}")
async def get_word_cloud(
    request: Request, thread_id: str, body: WordCloudRequest = Body(...)
):
    payload = request.state.user

    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    document_ids = body.document_ids
    max_words = body.max_words or 1000

    user_id = payload.userId

    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    thread = user["threads"].get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    stop_words_dir = f"data/{user_id}/threads/{thread_id}/stop_words"

    combined_text = ""
    combined_stop_words = set()

    # Combine text from matching parsed files
    if os.path.exists(parsed_dir):
        files_in_dir = os.listdir(parsed_dir)

        for file_name in files_in_dir:
            file_path = os.path.join(parsed_dir, file_name)

            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                data = json.loads(content)
                # Get document_id from the file - try both 'id' and 'document_id' fields
                file_document_id = data.get("id") or data.get("document_id")

                # Check if this document_id is in our requested list
                if file_document_id in body.document_ids:
                    text_content = data.get("full_text", "")
                    if text_content:
                        combined_text += text_content + " "
            except Exception as e:
                continue

    # Combine stop words from matching files
    if os.path.exists(stop_words_dir):
        files_in_stop_dir = os.listdir(stop_words_dir)

        for filename in files_in_stop_dir:
            if filename.endswith(".json"):
                file_path = os.path.join(stop_words_dir, filename)
                try:
                    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                        content = await f.read()
                    data = json.loads(content)
                    if isinstance(data, dict):
                        file_doc_id = data.get("document_id")
                        if file_doc_id in document_ids:
                            sw = data.get("stop_words", [])
                            combined_stop_words.update(sw)
                except Exception as e:
                    continue

    if not combined_text.strip():
        raise HTTPException(
            status_code=400, detail="No text found for the given document_ids"
        )

    # Generate word cloud
    try:
        img_bytes = await generate_word_cloud(
            combined_text, stop_words=list(combined_stop_words), max_words=max_words
        )

        from fastapi.responses import StreamingResponse

        return StreamingResponse(img_bytes, media_type="image/png")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate word cloud: {str(e)}"
        )


@router.get("/mindmap/{thread_id}")
async def get_mind_map(request: Request, thread_id: str):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    user_id = payload.userId
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    if len(thread.get("documents", [])) == 0:
        return {"mind_map": False, "message": "No documents found in the thread"}

    mind_map_dir = f"data/{user_id}/threads/{thread_id}/mind_maps"
    name = f"{user_id}_{thread_id}_global_mind_map.json"
    file_path = os.path.join(mind_map_dir, name)
    if os.path.exists(file_path):
        try:

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            data = json.loads(content)

            return {"mind_map": True, "status": True, "data": data, "message": ""}
        except Exception as e:
            pass

    if not thread.get("mindmap_enabled", False):
        return {"mind_map": False, "message": "Mind map generation not enabled"}
    else:
        return {
            "mind_map": True,
            "status": False,
            "message": "Mind map creation under progress...",
        }


@router.post("/summary")
async def get_summary(request: Request, body: MindMapRequest = Body(...)):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    document_id = body.document_id
    regenerate = body.regenerate
    print(f"Fetching summary for document_id: {document_id} in thread_id: {thread_id}")

    user_id = payload.userId
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    if not os.path.exists(parsed_dir):
        return {"error": "Parsed directory does not exist"}

    for filename in os.listdir(parsed_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(parsed_dir, filename)
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                data = json.loads(content)
                if isinstance(data, dict) and data.get("id") == document_id:
                    # On regenerate, clear existing summary and kick off generation
                    if regenerate:
                        data["summary"] = ""
                        data["_summary_status"] = "pending"
                        async with aiofiles.open(
                            file_path, "w", encoding="utf-8"
                        ) as write_f:
                            await write_f.write(json.dumps(data, ensure_ascii=False))

                        asyncio.create_task(
                            _generate_document_summary(data, file_path)
                        )
                        return {
                            "status": False,
                            "error": "Summary not yet generated. Generating...",
                        }

                    # Check if summary generation failed
                    if data.get("_summary_status") == "failed":
                        return {
                            "status": False,
                            "error": data.get(
                                "_summary_error", "Summary generation failed"
                            ),
                            "failed": True,
                        }

                    # Check if summary is being generated (pending)
                    if data.get("_summary_status") == "pending":
                        return {
                            "status": False,
                            "error": "Summary not yet generated. Generating...",
                        }

                    # Summary exists — return it
                    if data.get("summary"):
                        return {"status": True, "summary": data.get("summary")}

                    # No summary yet — trigger first-time on-demand generation
                    data["_summary_status"] = "pending"
                    async with aiofiles.open(
                        file_path, "w", encoding="utf-8"
                    ) as write_f:
                        await write_f.write(json.dumps(data, ensure_ascii=False))

                    asyncio.create_task(
                        _generate_document_summary(data, file_path)
                    )
                    return {
                        "status": False,
                        "error": "Summary not yet generated. Generating...",
                    }
            except Exception as e:
                continue

    return {"status": False, "error": "Document not found in parsed data", "failed": True}


async def _generate_document_summary(data: dict, file_path: str):
    """Background task to generate/regenerate a single document summary."""
    from core.models.document import Document
    from core.studio_features.summarizer import process_document_with_chunks

    try:
        doc = Document.model_validate(data)
        await process_document_with_chunks(doc)
        # Reload latest state to avoid race condition with concurrent writes
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            reread_content = await f.read()
        reread_data = json.loads(reread_content)
        reread_data["summary"] = doc.summary or ""
        reread_data.pop("_summary_status", None)
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(reread_data, ensure_ascii=False))
    except Exception as e:
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                err_content = await f.read()
            err_data = json.loads(err_content)
            err_data["_summary_status"] = "failed"
            err_data["_summary_error"] = str(e)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(err_data, ensure_ascii=False))
        except Exception:
            pass
        print(f"Failed generating individual summary: {e}")


@router.post("/summary/global")
async def get_global_summary(request: Request, body: GlobalSummaryRequest = Body(...)):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    regenerate = body.regenerate
    print(f"Fetching global summary for thread_id: {thread_id}")

    user_id = payload.userId
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    thread_dir = f"data/{user_id}/threads/{thread_id}"
    file_path = os.path.join(thread_dir, "global_summary.json")

    if regenerate and os.path.exists(file_path):
        os.remove(file_path)

    if not os.path.exists(file_path):
        # Write pending status to prevent duplicate tasks from subsequent polls
        await write_pending_status(file_path)

        from core.studio_features.summarizer import global_summarizer

        asyncio.create_task(global_summarizer(user_id, thread_id))

        return {
            "status": False,
            "error": "Global Summary not yet generated. Generating...",
        }

    gen_status = await read_generation_status(file_path)
    if gen_status is None:
        return {
            "status": False,
            "error": "Global Summary not yet generated. Generating...",
        }
    elif gen_status["state"] == "pending":
        return {
            "status": False,
            "error": "Global Summary not yet generated. Generating...",
        }
    elif gen_status["state"] == "failed":
        return {
            "status": False,
            "error": gen_status["error"],
            "failed": True,
        }
    elif gen_status["state"] == "completed":
        data = gen_status["data"]
        if isinstance(data, dict):
            if "error" in data:
                return {"status": False, "error": data["error"], "failed": True}
            return {"status": True, "summary": data.get("summary")}

    return {
        "status": False,
        "error": "Global Summary not yet generated. Generating...",
    }
