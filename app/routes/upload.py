from fastapi import APIRouter
from fastapi import UploadFile, File, Request
from typing import Annotated
from core.schemas.user import User
from core.config import Settings, db
from core.upload_files import upload_files
from core.parsers.process_files import process_files
from core.vectorstore import save_documents_to_chroma
import jwt
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

    jwt_token = None
    if "authorization" in request.headers:
        jwt_token = request.headers["authorization"].split(" ")[1]
    else:
        return {"error": "Authorization header missing"}

    if not jwt_token:
        return {"error": "JWT token is required"}

    if not Settings().SECRET_KEY:
        return {"error": "Secret key is not set in the environment"}
    try:
        payload = jwt.decode(jwt_token, Settings().SECRET_KEY, algorithms=["HS256"])
        try:
            user = User(**payload)
        except Exception as e:
            return {"error": f"Failed to create user from token payload: {str(e)}"}
    except jwt.ExpiredSignatureError:
        return {"error": "JWT token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid JWT token"}
    except Exception as e:
        return {"error": f"Failed to decode JWT token: {str(e)}"}

    
    # check whether the user exists in the database
    user_in_db = db.users.find_one({"user_id": user.user_id})
    if not user_in_db:
        return {"error": "User not found in the database"}
    # if thread id is not provided, create a new thread
    if not thread_id:
        thread_id = str(uuid.uuid4())
        # Insert a new thread in the threads array of user like {thread_id: thread_id, thread_name: thread_name}
        db.users.update_one(
            {"user_id": user.user_id},
            {"$push": {"threads": {"thread_id": thread_id, "thread_name": thread_name or "Untitled Thread"}}}
        )
    # if thread id is provided, check if the thread exists
    else:
        # Check if the thread exists
        thread = db.threads.find_one({"thread_id": thread_id, "user_id": user.user_id})
        if not thread:
            return {"error": "Thread not found for the user"}
        
    # Process each file
    raw_file_paths = await upload_files(files, user.user_id)
    if not raw_file_paths:
        return {"error": "No files uploaded or failed to upload files"}

    parsed_data = await process_files(raw_file_paths, thread_id, user.user_id)

    # add each document int he array of of documents of the thread of the user
    documents_to_add = [
        {
            "docId": doc.get("docId"),
            "title": doc.get("title"),
            "type": doc.get("type"),
            # get time from datetime
            "time_uploaded": datetime.datetime.now().isoformat(),
            "file_name": doc.get("file_name"),
            "content": doc.get("content"),
        }
        for doc in parsed_data.documents
    ]
    db.users.update_one(
        {"user_id": user.user_id, "threads.thread_id": thread_id},
        {"$push": {"threads.$.documents": {"$each": documents_to_add}}}
    )

    # call function to add parsed data to chroma db
    await save_documents_to_chroma(parsed_data, user.user_id, thread_id)