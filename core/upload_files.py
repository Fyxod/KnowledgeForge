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

    file_paths = []
    for file in files:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        name, ext = os.path.splitext(file.filename)
        filename = f"{name}_{timestamp}{ext}"
        file_path = os.path.join("data", user_id, "uploads", filename)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        file_paths.append(file_path)

    return file_paths
