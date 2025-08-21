from fastapi import APIRouter, Body, Request, HTTPException
import os
import json
from pydantic import BaseModel
from core.database import db
from core.word_cloud import generate_word_cloud
from app.socket_handler import sio

router = APIRouter(prefix="/extra", tags=["extra"])


class WordCloudRequest(BaseModel):
    thread_id: str
    document_ids: list[str]
    max_words: int | None = None


class MindMapRequest(BaseModel):
    thread_id: str
    document_id: str


@router.post("/wordcloud")
async def get_word_cloud(request: Request, body: WordCloudRequest = Body(...)):
    print("=== WORD CLOUD ENDPOINT START ===")
    print(f"Received payload: {body}")
    print(f"Thread ID: {body.thread_id}")
    print(f"Document IDs: {body.document_ids}")
    print(f"Max words: {body.max_words}")

    payload = request.state.user
    print(f"User payload: {payload}")
    
    if not payload:
        print("ERROR: User not authenticated")
        raise HTTPException(status_code=401, detail="User not authenticated")

    thread_id = body.thread_id
    document_ids = body.document_ids
    max_words = body.max_words or 1000

    user_id = payload.userId
    print(f"User ID: {user_id}")
    
    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        print("ERROR: User not found")
        raise HTTPException(status_code=404, detail="User not found")

    print(f"User found: {user.get('username', 'Unknown')}")

    thread = user["threads"].get(thread_id)
    if not thread:
        print(f"ERROR: Thread not found. Available threads: {list(user['threads'].keys())}")
        raise HTTPException(status_code=404, detail="Thread not found")

    print(f"Thread found: {thread.get('thread_name', 'Unknown')}")

    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    stop_words_dir = f"data/{user_id}/threads/{thread_id}/stop_words"
    print(f"Parsed directory: {parsed_dir}")
    print(f"Stop words directory: {stop_words_dir}")
    print(f"Parsed dir exists: {os.path.exists(parsed_dir)}")
    print(f"Stop words dir exists: {os.path.exists(stop_words_dir)}")
    
    combined_text = ""
    combined_stop_words = set()

    # Combine text from matching parsed files
    if os.path.exists(parsed_dir):
        files_in_dir = os.listdir(parsed_dir)
        print(f"Files in parsed directory: {files_in_dir}")
        
        for file_name in files_in_dir:
            print(f"Processing file: {file_name}")
            file_path = os.path.join(parsed_dir, file_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"File data keys: {list(data.keys())}")
                    
                    # Get document_id from the file - try both 'id' and 'document_id' fields
                    file_document_id = data.get('id') or data.get('document_id')
                    print(f"File document_id: {file_document_id}")
                    print(f"Looking for document_ids: {body.document_ids}")
                    
                    # Check if this document_id is in our requested list
                    if file_document_id in body.document_ids:
                        print(f"Match found: True")
                        text_content = data.get('full_text', '')
                        if text_content:
                            combined_text += text_content + " "
                            print(f"Added text from {file_name}: {len(text_content)} characters")
                        else:
                            print(f"No full_text found in {file_name}")
                    else:
                        print(f"Match found: False")
                        print(f"Document ID {file_document_id} not in requested IDs {body.document_ids}")
            except Exception as e:
                print(f"Error processing file {file_name}: {e}")
                continue
    else:
        print("Parsed directory does not exist")

    # Combine stop words from matching files
    if os.path.exists(stop_words_dir):
        files_in_stop_dir = os.listdir(stop_words_dir)
        print(f"Files in stop words directory: {files_in_stop_dir}")
        
        for filename in files_in_stop_dir:
            if filename.endswith(".json"):
                file_path = os.path.join(stop_words_dir, filename)
                print(f"Processing stop words file: {filename}")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict):
                        file_doc_id = data.get("document_id")
                        if file_doc_id in document_ids:
                            sw = data.get("stop_words", [])
                            print(f"Stop words from {filename}: {len(sw)} words")
                            combined_stop_words.update(sw)
                except Exception as e:
                    print(f"Error processing stop words file {filename}: {str(e)}")
                    continue
    else:
        print("Stop words directory does not exist")

    print(f"Combined text length: {len(combined_text)} characters")
    print(f"Combined text preview: {combined_text[:200]}...")
    print(f"Combined stop words count: {len(combined_stop_words)}")

    if not combined_text.strip():
        print("ERROR: No text found for the given document_ids")
        raise HTTPException(status_code=400, detail="No text found for the given document_ids")

    # Generate word cloud
    try:
        print("=== STARTING WORD CLOUD GENERATION ===")
        print(f"Calling generate_word_cloud with text length: {len(combined_text)}")
        print(f"Stop words count: {len(combined_stop_words)}")
        print(f"Max words: {max_words}")
        
        img_bytes = await generate_word_cloud(
            combined_text, stop_words=list(combined_stop_words), max_words=max_words
        )
        
        print(f"Word cloud generated successfully")
        print(f"Image bytes type: {type(img_bytes)}")
        print(f"Image bytes size: {len(img_bytes) if hasattr(img_bytes, '__len__') else 'Unknown'}")
        
        from fastapi.responses import StreamingResponse
        
        print("=== RETURNING STREAMING RESPONSE ===")
        return StreamingResponse(img_bytes, media_type="image/png")
        
    except Exception as e:
        print(f"ERROR during word cloud generation: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate word cloud: {str(e)}")


@router.post("/mindmap")
async def get_mind_map(request: Request, body: MindMapRequest = Body(...)):

    payload = request.state.user
    
    print(f"Received mind map request: {body}")
    print(f"payload  {payload}")

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    document_id = body.document_id
    
    # Get client socket ID from headers (if provided)
    client_socket_id = request.headers.get("x-socket-id")

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
    
    # Emit progress update - Starting search
    if client_socket_id:
        await sio.emit("mindmap_progress", {
            "status": "searching",
            "message": "Searching for existing mind map...",
            "progress": 20
        }, to=client_socket_id)
    
    if not os.path.exists(mind_map_dir):
        # Emit progress update - No directory, mind map not generated yet
        if client_socket_id:
            await sio.emit("mindmap_progress", {
                "status": "not_found",
                "message": "Mind map not available. Generated during document processing.",
                "progress": 100
            }, to=client_socket_id)
        
        # Return success status with not_found indicator to avoid API error handling
        return {"status": True, "not_found": True, "message": "No mind map found for the given document_id"}

    # Emit progress update - Checking files
    if client_socket_id:
        await sio.emit("mindmap_progress", {
            "status": "checking",
            "message": "Checking available mind maps...",
            "progress": 50
        }, to=client_socket_id)

    for filename in os.listdir(mind_map_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(mind_map_dir, filename)
            try:
                # Emit progress update - Loading file
                if client_socket_id:
                    await sio.emit("mindmap_progress", {
                        "status": "loading",
                        "message": f"Loading mind map...",
                        "progress": 80
                    }, to=client_socket_id)
                
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("document_id") == document_id:
                    # Emit success
                    if client_socket_id:
                        await sio.emit("mindmap_progress", {
                            "status": "success",
                            "message": "Mind map loaded successfully!",
                            "progress": 100
                        }, to=client_socket_id)
                    
                    return {"status": True, "mind_map": data}
            except Exception as e:
                continue

    # Mind map not found in any file
    if client_socket_id:
        await sio.emit("mindmap_progress", {
            "status": "not_found",
            "message": "Mind map not available for this document",
            "progress": 100
        }, to=client_socket_id)
    
    # Return success status with not_found indicator to avoid API error handling
    return {"status": True, "not_found": True, "message": "No mind map found for the given document_id"}


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
