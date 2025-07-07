import aiofiles
import os
from datetime import datetime
from typing import List

async def upload_files(files, user_id) -> List[str]:
    """
    Asynchronously upload each file to {user_id}/uploads inside data directory
    as filename_{timestamp}.{extension}. Returns a list of file paths.
    """
    
    os.makedirs(f"data/{user_id}/uploads", exist_ok=True)

    files_data = []
    for file in files:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        name, ext = os.path.splitext(file.filename)
        file_name = f"{name}_{timestamp}{ext}"
        file_path = os.path.join("data", user_id, "uploads", file_name)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        files_data.append({
            "title": file.filename,
            "file_name": file_name,
            "path": file_path,
        })

    return files_data
