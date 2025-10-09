import os
from datetime import datetime
from typing import List
from app.socket_handler import sio
import aiofiles


async def upload_files(files, user_id: str, thread_id: str) -> List[dict]:
    """
    Asynchronously upload each file to the 'data/{user_id}/threads/{thread_id}/uploads' directory.
    Each file is renamed to include a timestamp: filename_{timestamp}.{extension}.

    Args:
        files (list): List of UploadFile objects.
        user_id (str): Unique identifier for the user.

    Returns:
        List[dict]: List of metadata dictionaries for each uploaded file.
    """
    upload_dir = os.path.join("data", user_id, "threads", thread_id, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    files_data = []

    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name, ext = os.path.splitext(file.filename)
        file_name = f"{name}_{timestamp}{ext}"
        file_path = os.path.join(upload_dir, file_name)
        await sio.emit(f"{user_id}/progress", {"message": f"Uploading {file.filename}"})

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        await sio.emit(f"{user_id}/progress", {"message": f"Uploaded {file.filename}"})

        files_data.append(
            {
                "title": file.filename,
                "file_name": file_name,
                "path": file_path,
            }
        )

    return files_data
