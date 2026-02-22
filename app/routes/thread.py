"""
Routes for thread management functionality.
"""

import datetime
import uuid
from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from core.database import db
from core.models.thread import (
    InstructionCreateRequest,
    InstructionUpdateRequest,
    ThreadCreateRequest,
    ThreadUpdateRequest,
)

router = APIRouter(prefix="/thread", tags=["thread"])


# ── Helpers ──


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


# ── Thread CRUD ──


@router.post("/")
async def create_thread(request: Request, thread_data: ThreadCreateRequest):
    """Create a new empty thread for the user."""

    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

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
            "instructions": [],
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
    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

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

    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    return {"status": "success", "threads": user.get("threads", {})}


@router.put("/{thread_id}")
async def update_thread(
    request: Request, thread_id: str, thread_data: ThreadUpdateRequest
):
    """Update thread name."""
    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

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


# ── Thread Instructions ──


@router.get("/{thread_id}/instructions")
async def get_instructions(request: Request, thread_id: str):
    """Get all instructions for a thread."""
    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    thread = user.get("threads", {}).get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    return {
        "status": "success",
        "instructions": thread.get("instructions", []),
    }


@router.post("/{thread_id}/instructions")
async def add_instruction(
    request: Request, thread_id: str, body: InstructionCreateRequest
):
    """Add a new instruction to a thread."""
    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

    if thread_id not in user.get("threads", {}):
        return {"error": "Thread not found"}

    instruction = {
        "id": str(uuid.uuid4())[:8],
        "text": body.text,
        "selected": True,
    }

    now = datetime.datetime.now(datetime.timezone.utc)
    db.users.update_one(
        {"userId": user_id},
        {
            "$push": {f"threads.{thread_id}.instructions": instruction},
            "$set": {f"threads.{thread_id}.updatedAt": now},
        },
    )

    return {
        "status": "success",
        "instruction": instruction,
    }


@router.put("/{thread_id}/instructions/{instruction_id}")
async def update_instruction(
    request: Request,
    thread_id: str,
    instruction_id: str,
    body: InstructionUpdateRequest,
):
    """Update an instruction's text or selected state."""
    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

    thread = user.get("threads", {}).get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    instructions = thread.get("instructions", [])
    idx = next(
        (i for i, ins in enumerate(instructions) if ins["id"] == instruction_id), None
    )
    if idx is None:
        return {"error": "Instruction not found"}

    update_fields = {}
    now = datetime.datetime.now(datetime.timezone.utc)
    if body.text is not None:
        update_fields[f"threads.{thread_id}.instructions.{idx}.text"] = body.text
    if body.selected is not None:
        update_fields[f"threads.{thread_id}.instructions.{idx}.selected"] = (
            body.selected
        )
    update_fields[f"threads.{thread_id}.updatedAt"] = now

    db.users.update_one({"userId": user_id}, {"$set": update_fields})

    # Return updated instruction
    updated = instructions[idx].copy()
    if body.text is not None:
        updated["text"] = body.text
    if body.selected is not None:
        updated["selected"] = body.selected

    return {
        "status": "success",
        "instruction": updated,
    }


@router.delete("/{thread_id}/instructions/{instruction_id}")
async def delete_instruction(request: Request, thread_id: str, instruction_id: str):
    """Delete an instruction from a thread."""
    payload, user, error_response = _get_authenticated_user(request)
    if error_response:
        return error_response

    user_id = payload.userId

    thread = user.get("threads", {}).get(thread_id)
    if not thread:
        return {"error": "Thread not found"}

    instructions = thread.get("instructions", [])
    updated_instructions = [ins for ins in instructions if ins["id"] != instruction_id]

    if len(updated_instructions) == len(instructions):
        return {"error": "Instruction not found"}

    now = datetime.datetime.now(datetime.timezone.utc)
    db.users.update_one(
        {"userId": user_id},
        {
            "$set": {
                f"threads.{thread_id}.instructions": updated_instructions,
                f"threads.{thread_id}.updatedAt": now,
            }
        },
    )

    return {
        "status": "success",
        "message": "Instruction deleted successfully",
    }
