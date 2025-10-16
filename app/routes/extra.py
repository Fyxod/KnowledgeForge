import aiofiles
from fastapi import APIRouter, Body, Request, HTTPException
import os
import json
from pydantic import BaseModel
from core.database import db
from core.word_cloud import generate_word_cloud
from app.socket_handler import sio

router = APIRouter(prefix="", tags=["extra"])


class WordCloudRequest(BaseModel):
    document_ids: list[str]
    max_words: int | None = None


class MindMapRequest(BaseModel):
    thread_id: str
    document_id: str


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
                if isinstance(data, dict) and data.get("document_id") == document_id:
                    return {"status": True, "summary": data.get("summary")}
            except Exception as e:
                continue

    return {"status": False, "message": "No summary found for the given document_id"}
