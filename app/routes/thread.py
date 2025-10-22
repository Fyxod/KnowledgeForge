"""
Routes for thread management functionality.
"""

import datetime
import uuid
from fastapi import APIRouter, Request, Body
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
            "extra_done": False,
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


@router.get("/{thread_id}")
async def get_thread(request: Request, thread_id: str):
    """Get a specific thread for the authenticated user."""
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

    return {
        "status": "success",
        "thread": user["threads"][thread_id],
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


class ThreadUpdateRequest(BaseModel):
    thread_name: str


@router.delete("/delete/{thread_id}")
async def delete_thread(request: Request, thread_id: str):
    """Delete a thread for the authenticated user."""
    payload = request.state.user
    if not payload:
        return {"status": False, "error": "User not authenticated"}

    user_id = payload.userId

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


@router.delete("/{thread_id}")
async def delete_thread(request: Request, thread_id: str):
    """Delete a thread for the authenticated user."""

    payload = request.state.user
    if not payload:
        print(f"DELETE /thread/{thread_id} - User not authenticated")
        return {"error": "User not authenticated"}

    user_id = payload.userId

    print(f"DELETE /thread/{thread_id} - User ID: {user_id}")

    if not thread_id:
        print(f"DELETE /thread/{thread_id} - Thread ID is required")
        return {"error": "Thread ID is required"}

    # Find user in DB
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        print(f"DELETE /thread/{thread_id} - User not found")
        return {"error": "User not found"}

    # Check if thread exists
    if thread_id not in user.get("threads", {}):
        print(f"DELETE /thread/{thread_id} - Thread not found")
        return {"error": "Thread not found"}

    try:
        # Remove thread from user
        result = db.users.update_one(
            {"userId": user_id}, {"$unset": {f"threads.{thread_id}": ""}}
        )

        if result.modified_count > 0:
            print(f"DELETE /thread/{thread_id} - Thread deleted successfully")
            return {
                "status": "success",
                "message": "Thread deleted successfully",
                "thread_id": thread_id,
            }
        else:
            print(f"DELETE /thread/{thread_id} - No documents modified")
            return {
                "status": "error",
                "message": "Failed to delete thread - no documents modified",
                "thread_id": thread_id,
            }
    except Exception as e:
        print(f"DELETE /thread/{thread_id} - Error deleting thread: {str(e)}")
        return {"error": f"Error deleting thread: {str(e)}"}
