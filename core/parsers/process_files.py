import json
import os
from typing import List

import aiofiles
import asyncio

from app.socket_handler import sio
from core.models.document import Documents
from core.parsers.main import extract_document
import time


# ppt, pdf, xlsx, docx, txt, html, png, jpeg, jpg, md
async def process_files(
    files_data: List[dict],
    user_id: str,
    thread_id: str,
) -> Documents:
    """
    Process a list of uploaded files:
    - Pass each file to the document parser.
    - Store the parsed result as JSON in `data/{user_id}/threads/{thread_id}/parsed/`.
    - Accumulate all parsed documents into a Documents object.

    Returns:
        Documents: A structured object containing parsed documents.
    """
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    documents = Documents(documents=[], thread_id=thread_id, user_id=user_id)
    start_time = time.time()

    # Helper to process one file
    async def process_file(file_data):
        await sio.emit(
            f"{user_id}/progress", {"message": f"Processing {file_data['title']}"}
        )
        parsed_data = await extract_document(
            path=file_data["path"],
            title=file_data["title"],
            file_name=file_data["file_name"],
            user_id=user_id,
            thread_id=thread_id,
        )

        if parsed_data is None:
            print(
                f"Warning: Failed to parse file {file_data['file_name']}, skipping..."
            )
            return None

        parsed_dict = parsed_data.model_dump()
        parsed_dict["thread_id"] = thread_id
        parsed_dict["user_id"] = user_id
        parsed_json = json.dumps(parsed_dict, indent=2, ensure_ascii=False)

        name, _ = os.path.splitext(file_data["file_name"])
        json_file_path = os.path.join(parsed_dir, f"{name}.json")

        async with aiofiles.open(json_file_path, "w", encoding="utf-8") as f:
            await f.write(parsed_json)

        return parsed_data

    batch_size = 10
    # Process in batches
    for i in range(0, len(files_data), batch_size):
        batch = files_data[i : i + batch_size]
        results = await asyncio.gather(
            *(process_file(file_data) for file_data in batch)
        )
        for result in results:
            if result:
                documents.documents.append(result)

    end_time = time.time()
    print(f"Processed {len(files_data)} files in {end_time - start_time:.2f} seconds")
    return documents
