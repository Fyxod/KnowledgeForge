from fastapi import APIRouter
from fastapi import UploadFile, File, Request, Form
from typing import Annotated, Optional
from core.schemas.user import UserJwtPayload
from core.config import Settings
from core.database import db
from core.upload_files import upload_files
from core.parsers.process_files import process_files
from core.vectorstore import save_documents_to_store
import uuid
import datetime
router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload_file(
    request: Request,
    files: Annotated[list[UploadFile], File()],
    thread_name: Annotated[Optional[str], Form()] = None,
    thread_id: Annotated[Optional[str], Form()] = None,
):
    
    """Handle multiple file uploads."""

    print(f"Thread name: {thread_name}")
    print(f"Thread ID: {thread_id}")
    print(f"Files: {files}")
    if not files:
        return {"error": "No files uploaded"}
    payload = request.state.user
    if not payload:
        return {"error": "User not authenticated"}
    
    user_id = payload.userId

    # Find user in DB
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    
    if not user:
        return {"error": "User not found"}
    print(f"User found: {user}")
    
    now = datetime.datetime.now(datetime.timezone.utc)

    # Create new thread if thread_id is not provided
    if not thread_id:
        print("Creating a new thread")
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
        print(f"Updating existing thread with ID: {thread_id}")
        if thread_id not in user.get("threads", {}).keys():
            return {"error": "Thread not found for the user"}

        db.users.update_one(
            {"userId": user_id},
            {"$set": {f"threads.{thread_id}.updatedAt": now}}
        )

    # Upload and parse files
    files_data = await upload_files(files, user_id)
    if not files_data:
        return {"error": "No files uploaded or failed to upload files"}

    print(f"Raw file paths: {files_data}")

    parsed_data = await process_files(files_data, user_id, thread_id)
    json_data = parsed_data.model_dump_json()

    # dump to json file
    with open(f"parsed_data_{thread_id}.json", "w") as f:
        f.write(json_data)
    # Build document objects

    parsed_data_dict = parsed_data.model_dump()
    documents_to_add = [
        {
            "docId": doc.get("id"),
            "title": doc.get("title"),
            "type": doc.get("type"),
            "time_uploaded": now,
            "file_name": doc.get("file_name"),
        }
        for doc in parsed_data_dict["documents"]
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
    await save_documents_to_store(parsed_data, user_id, thread_id)

    return {"status": "success", "message": "Files uploaded and processed", "thread_id": thread_id, "documents": documents_to_add}
