from fastapi import APIRouter
from fastapi import UploadFile, File, Request
from typing import Annotated
from core.schemas.user import UserJwtPayload
from core.config import Settings
from core.database import db
from core.upload_files import upload_files
from core.parsers.process_files import process_files
from core.vectorstore import save_documents_to_chroma
import uuid
import datetime
router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload_file(
    request: Request,
    thread_name: str = None,
    thread_id: str = None,
    files: Annotated[list[UploadFile], File()] = None,
):
    """Handle multiple file uploads."""
    payload = request.state.user
    if not payload:
        return {"error": "User not authenticated"}
    
    user_id = payload.userId

    # Find user in DB
    user_in_db = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user_in_db:
        return {"error": "User not found"}

    now = datetime.utcnow()

    # Create new thread if thread_id is not provided
    if not thread_id:
        thread_id = str(uuid.uuid4())
        new_thread = {
            f"threads.{thread_id}": {
                "thread_name": thread_name or "New Thread",
                "documents": [],
                "chats": [],
                "createdAt": now,
                "updatedAt": now,
            }
        }
        db.users.update_one({"userId": user_id}, {"$set": new_thread})
    else:
        if f"threads.{thread_id}" not in user_in_db.get("threads", {}):
            return {"error": "Thread not found for the user"}

        db.users.update_one(
            {"userId": user_id},
            {"$set": {f"threads.{thread_id}.updatedAt": now}}
        )

    # Upload and parse files
    raw_file_paths = await upload_files(files, user_id)
    if not raw_file_paths:
        return {"error": "No files uploaded or failed to upload files"}

    parsed_data = await process_files(raw_file_paths, user_id, thread_id)

    # Build document objects
    documents_to_add = [
        {
            "docId": doc.get("docId"),
            "title": doc.get("title"),
            "type": doc.get("type"),
            "time_uploaded": now,
            "file_name": doc.get("file_name"),
        }
        for doc in parsed_data.documents
    ]

    # Add document objects to the thread
    db.users.update_one(
        {"userId": user_id},
        {
            "$push": {f"threads.{thread_id}.documents": {"$each": documents_to_add}},
            "$set": {f"threads.{thread_id}.updatedAt": now}
        }
    )

    # Save to vector store
    await save_documents_to_chroma(parsed_data, user_id, thread_id)

    return {"message": "Files uploaded and processed", "thread_id": thread_id, "documents": documents_to_add}
