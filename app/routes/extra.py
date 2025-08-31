import aiofiles
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

class GlobalMindMapRequest(BaseModel):
    thread_id: str
    document_id: str


@router.post("/wordcloud")
async def get_word_cloud(request: Request, body: WordCloudRequest = Body(...)):
    payload = request.state.user
    
    if not payload:
        raise HTTPException(status_code=401, detail="User not authenticated")

    thread_id = body.thread_id
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
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                data = json.loads(content)
                # Get document_id from the file - try both 'id' and 'document_id' fields
                file_document_id = data.get('id') or data.get('document_id')
                
                # Check if this document_id is in our requested list
                if file_document_id in body.document_ids:
                    text_content = data.get('full_text', '')
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
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
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
        raise HTTPException(status_code=400, detail="No text found for the given document_ids")

    # Generate word cloud
    try:
        img_bytes = await generate_word_cloud(
            combined_text, stop_words=list(combined_stop_words), max_words=max_words
        )
        
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(img_bytes, media_type="image/png")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate word cloud: {str(e)}")


@router.post("/mindmap")
async def get_mind_map(request: Request, body: MindMapRequest = Body(...)):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    document_id = body.document_id
    
    # Get client socket ID from headers (if provided)
    client_socket_id = request.headers.get("x-socket-id")

    user_id = payload.userId
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
                "message": "   ",
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
                
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                data = json.loads(content)
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
            "message": "   ",
            "progress": 100
        }, to=client_socket_id)
    
    # Return success status with not_found indicator to avoid API error handling
    return {"status": True, "not_found": True, "message": "No mind map found for the given document_id"}


@router.post("/mindmap/global")
async def get_mind_map(request: Request, body: GlobalMindMapRequest = Body(...)):

    payload = request.state.user

    if not payload:
        return {"error": "User not authenticated"}

    thread_id = body.thread_id
    
    # Get client socket ID from headers (if provided)
    client_socket_id = request.headers.get("x-socket-id")

    user_id = payload.userId
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
                "message": "  ",
                "progress": 100
            }, to=client_socket_id)
        
        # Return success status with not_found indicator to avoid API error handling
        return {"status": True, "not_found": True, "message": "Global Mind Map not found"}

    # Emit progress update - Checking files
    if client_socket_id:
        await sio.emit("mindmap_progress", {
            "status": "checking",
            "message": "Checking available mind maps...",
            "progress": 50
        }, to=client_socket_id)

    name = f"{user_id}_{thread_id}_global_mind_map.json"
    file_path = os.path.join(mind_map_dir, name)
    if os.path.exists(file_path):
        try:
            # Emit progress update - Loading file
            if client_socket_id:
                await sio.emit("mindmap_progress", {
                    "status": "loading",
                    "message": f"Loading global mind map...",
                    "progress": 80
                }, to=client_socket_id)

            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            data = json.loads(content)
            # Emit success
            if client_socket_id:
                await sio.emit("mindmap_progress", {
                    "status": "success",
                    "message": "Global mind map loaded successfully!",
                    "progress": 100
                }, to=client_socket_id)
            return {"status": True, "mind_map": data}
        except Exception as e:
            pass

    # Mind map not found in any file
    if client_socket_id:
        await sio.emit("mindmap_progress", {
            "status": "not_found",
            "message": "   ",
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
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                data = json.loads(content)
                if isinstance(data, dict) and data.get("document_id") == document_id:
                    return {"status": True, "summary": data.get("summary")}
            except Exception as e:
                continue

    return {"status": False, "message": "No summary found for the given document_id"}
