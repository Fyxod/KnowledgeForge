import json
import os
from typing import List

import aiofiles

from core.models.document import Documents
from core.parsers.main import extract_document


async def process_files(
    files_data: List[dict],
    user_id: str,
    thread_id: str,
) -> Documents:
    """
    Process a list of uploaded files:
    - Pass each file to the document parser.
    - Store the parsed result as JSON in `data/{user_id}/parsed/`.
    - Accumulate all parsed documents into a Documents object.

    Returns:
        Documents: A structured object containing parsed documents.
    """
    parsed_dir = f"data/{user_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    documents = Documents(documents=[], thread_id=thread_id, user_id=user_id)

    for file_data in files_data:
        parsed_data = await extract_document(
            path=file_data["path"],
            title=file_data["title"],
            file_name=file_data["file_name"],
            user_id=user_id,
        )

        # Prepare JSON-serializable data
        parsed_dict = parsed_data.model_dump()
        parsed_dict["thread_id"] = thread_id
        parsed_dict["user_id"] = user_id
        parsed_json = json.dumps(parsed_dict)

        # Save parsed output as json file
        name, _ = os.path.splitext(file_data["file_name"])
        json_file_path = os.path.join(parsed_dir, f"{name}.json")

        async with aiofiles.open(json_file_path, "w") as f:
            await f.write(parsed_json)

        documents.documents.append(parsed_data)

    return documents
