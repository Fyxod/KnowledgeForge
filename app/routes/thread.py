"""
Routes for thread management functionality.
"""

import datetime
import uuid
from fastapi import APIRouter, Request
from pydantic import BaseModel
from core.database import db

router = APIRouter(prefix="/thread", tags=["thread"])


class ThreadCreateRequest(BaseModel):
    thread_name: str = "New Chat"


@router.post("/")
async def create_thread(request: Request, thread_data: ThreadCreateRequest):
    """Create a new empty thread for the user."""

    payload = request.state.user
    if not payload:
        return {"error": "User not authenticated"}

    user_id = payload.userId

    # Find user in DB
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    # Create new thread
    thread_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)

    new_thread = {
        f"threads.{thread_id}": {
            "thread_name": thread_data.thread_name,
            "documents": [],
            "chats": [],
            "createdAt": now,
            "updatedAt": now,
        }
    }

    # Add thread to user
    db.users.update_one({"userId": user_id}, {"$set": new_thread})

    return {
        "status": "success",
        "message": "Thread created successfully",
        "thread_id": thread_id,
        "thread_name": thread_data.thread_name,
    }


@router.get("/")
async def get_threads(request: Request):
    """Get all threads for the authenticated user."""

    payload = request.state.user
    if not payload:
        return {"error": "User not authenticated"}

    user_id = payload.userId

    # Find user in DB
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    return {"status": "success", "threads": user.get("threads", {})}


class ThreadDeleteRequest(BaseModel):
    thread_id: str


class ThreadUpdateRequest(BaseModel):
    thread_name: str


@router.delete("/delete")
async def delete_thread(request: Request, thread_data: ThreadDeleteRequest):
    """Delete a thread for the authenticated user."""
    payload = request.state.user
    if not payload:
        return {"status": False, "error": "User not authenticated"}

    user_id = payload.userId
    thread_id = thread_data.thread_id

    # Find user in DB
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"status": False, "error": "User not found"}

    # Check if thread exists
    if thread_id not in user.get("threads", {}):
        return {"status": False, "error": "Thread not found"}

    # Delete thread
    result = db.users.update_one(
        {"userId": user_id}, {"$unset": {f"threads.{thread_id}": ""}}
    )

    if result.modified_count == 1:
        return {"status": True}
    else:
        return {"status": False}


@router.put("/{thread_id}")
async def update_thread(
    request: Request, thread_id: str, thread_data: ThreadUpdateRequest
):
    """Update thread name."""
    payload = request.state.user
    if not payload:
        return {"error": "User not authenticated"}

    user_id = payload.userId

    # Find user in DB
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return {"error": "User not found"}

    # Check if thread exists
    if thread_id not in user.get("threads", {}):
        return {"error": "Thread not found"}

    # Update thread name
    now = datetime.datetime.now(datetime.timezone.utc)
    db.users.update_one(
        {"userId": user_id},
        {
            "$set": {
                f"threads.{thread_id}.thread_name": thread_data.thread_name,
                f"threads.{thread_id}.updatedAt": now,
            }
        },
    )

    return {
        "status": "success",
        "message": "Thread name updated successfully",
        "thread_id": thread_id,
        "thread_name": thread_data.thread_name,
    }
