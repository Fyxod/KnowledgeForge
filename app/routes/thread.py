"""
Routes for thread management functionality.
"""

import asyncio
import datetime
import os
import shutil
import uuid
from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from core.database import db
from core.embeddings.vectorstore import delete_document_from_chroma, rebuild_bm25_after_deletion

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
    thread_id = str(uuid.uuid4())[:7]
    now = datetime.datetime.now(datetime.timezone.utc)

    new_thread = {
        f"threads.{thread_id}": {
            "thread_name": thread_data.thread_name,
            "documents": [],
            "chats": [],
            "createdAt": now,
            "updatedAt": now,
            "extra_done": False,
            "mindmap_enabled": False,
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


def _get_authenticated_user(request: Request):
    """Retrieve the authenticated user payload and database document."""

    payload = request.state.user
    if not payload:
        return None, None, {"error": "User not authenticated"}

    user_id = payload.userId

    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        return None, None, {"error": "User not found"}

    return payload, user, None



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

    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        print(f"DELETE /thread/{thread_id} - {error_response['error']}")
        return error_response

    user_id = payload.userId

    print(f"DELETE /thread/{thread_id} - User ID: {user_id}")

    if not thread_id:
        print(f"DELETE /thread/{thread_id} - Thread ID is required")
        return {"error": "Thread ID is required"}

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


@router.delete("/{thread_id}/document/{doc_id}")
async def delete_document(request: Request, thread_id: str, doc_id: str):
    """Delete a specific document from a thread, cleaning up all storage."""

    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

    thread = user.get("threads", {}).get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    documents = thread.get("documents", [])
    doc_entry = next((d for d in documents if d.get("docId") == doc_id), None)
    if not doc_entry:
        return {"error": "Document not found in thread"}

    file_name = doc_entry.get("file_name", "")

    try:
        # 1. Remove from MongoDB
        now = datetime.datetime.now(datetime.timezone.utc)
        db.users.update_one(
            {"userId": user_id},
            {
                "$pull": {f"threads.{thread_id}.documents": {"docId": doc_id}},
                "$set": {f"threads.{thread_id}.updatedAt": now},
            },
        )

        # 2. Delete from ChromaDB
        try:
            await delete_document_from_chroma(user_id, thread_id, doc_id)
        except Exception as e:
            print(f"Warning: ChromaDB cleanup failed for doc {doc_id}: {e}")

        # 3. Rebuild BM25 index
        try:
            await asyncio.to_thread(
                rebuild_bm25_after_deletion, user_id, thread_id, doc_id
            )
        except Exception as e:
            print(f"Warning: BM25 rebuild failed for thread {thread_id}: {e}")

        # 4. Delete uploaded file from disk
        if file_name:
            upload_path = os.path.join(
                "data", user_id, "threads", thread_id, "uploads", file_name
            )
            if os.path.exists(upload_path):
                os.remove(upload_path)

        # 5. Delete parsed JSON from disk
        if file_name:
            name_without_ext = os.path.splitext(file_name)[0]
            parsed_path = os.path.join(
                "data", user_id, "threads", thread_id, "parsed",
                f"{name_without_ext}.json",
            )
            if os.path.exists(parsed_path):
                os.remove(parsed_path)

        # 6. Delete extracted images directory from disk
        if file_name:
            name_without_ext = os.path.splitext(file_name)[0]
            images_dir = os.path.join(
                "data", user_id, "threads", thread_id, "images", name_without_ext
            )
            if os.path.isdir(images_dir):
                shutil.rmtree(images_dir, ignore_errors=True)

        # Return updated documents list
        updated_user = db.users.find_one(
            {"userId": user_id}, {"_id": 0, "password": 0}
        )
        updated_docs = (
            updated_user.get("threads", {}).get(thread_id, {}).get("documents", [])
            if updated_user
            else []
        )

        return {
            "status": "success",
            "message": "Document deleted successfully",
            "thread_id": thread_id,
            "deleted_doc_id": doc_id,
            "documents": jsonable_encoder(updated_docs),
        }

    except Exception as e:
        print(f"Error deleting document {doc_id} from thread {thread_id}: {e}")
        return {"error": f"Failed to delete document: {str(e)}"}


@router.delete("/{thread_id}/chats/{chat_index}")
async def delete_chat_from_thread(request: Request, thread_id: str, chat_index: int):
    """Delete a specific chat message by index from a thread."""

    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

    thread = user.get("threads", {}).get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    chats = thread.get("chats", [])

    if not isinstance(chat_index, int) or chat_index < 0 or chat_index >= len(chats):
        return {"error": "Invalid chat index"}

    updated_chats = chats[:chat_index] + chats[chat_index + 1 :]

    now = datetime.datetime.now(datetime.timezone.utc)

    db.users.update_one(
        {"userId": user_id},
        {
            "$set": {
                f"threads.{thread_id}.chats": updated_chats,
                f"threads.{thread_id}.updatedAt": now,
            }
        },
    )

    return {
        "status": "success",
        "message": "Chat deleted successfully",
        "thread_id": thread_id,
        "deleted_index": chat_index,
        "chats": jsonable_encoder(updated_chats),
    }


@router.delete("/{thread_id}/chats")
async def clear_thread_chats(request: Request, thread_id: str):
    """Remove all chat messages from a thread."""

    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

    if thread_id not in user.get("threads", {}):
        return {"error": "Thread not found"}

    now = datetime.datetime.now(datetime.timezone.utc)

    db.users.update_one(
        {"userId": user_id},
        {
            "$set": {
                f"threads.{thread_id}.chats": [],
                f"threads.{thread_id}.updatedAt": now,
            }
        },
    )

    return {
        "status": "success",
        "message": "All chats cleared successfully",
        "thread_id": thread_id,
        "chats": [],
    }
