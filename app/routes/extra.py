from fastapi import APIRouter, Body, Request
import os
import json
from pydantic import BaseModel
from core.database import db

router = APIRouter(prefix="/", tags=["extra"])


class MindMapRequest(BaseModel):
    thread_id: str
    document_id: str


@router.post("/mindmap")
async def get_mind_map(request: Request, body: MindMapRequest = Body(...)):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    document_id = body.document_id

    print(
        f"Received mind map request for thread_id: {thread_id} and document_id: {document_id}"
    )

    user_id = payload.userId
    print(f"User ID from payload: {user_id}")
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    thread = user["threads"].get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    mind_map_dir = f"data/{user_id}/threads/{thread_id}/mind_maps"
    if not os.path.exists(mind_map_dir):
        return {"error": "Mind map directory does not exist"}

    for filename in os.listdir(mind_map_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(mind_map_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("document_id") == document_id:
                    return {"status": True, "mind_map": data}
            except Exception as e:
                continue

    return {"status": False, "message": "No mind map found for the given document_id"}

@router.post("/summary")
async def get_summary(request: Request, body: MindMapRequest = Body(...)):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    document_id = body.document_id

    print(
        f"Received summary request for thread_id: {thread_id} and document_id: {document_id}"
    )

    user_id = payload.userId
    print(f"User ID from payload: {user_id}")
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
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("document_id") == document_id:
                    return {"status": True, "summary": data.get("summary")}
            except Exception as e:
                continue

    return {"status": False, "message": "No summary found for the given document_id"}
