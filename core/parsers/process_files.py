import os
from core.schemas.document import Documents
from core.parsers.main_parser import extract_document
import aiofiles
import json
from typing import List

async def process_files(
    files_data: List[dict],
    user_id: str,
    thread_id: str,
) -> dict:
    """
    pass all the files to main parser and return the parsed data
    and save them in an array according to the Documents model,
    return the array
    """

    os.makedirs(f"data/{user_id}/parsed", exist_ok=True)
    documents = Documents(documents=[], thread_id=thread_id, user_id=user_id)

    for file_data in files_data:
        # Call the main parser for each file and append the result to the documents array
        parsed_data = await extract_document(path=file_data["path"], title=file_data["title"], file_name=file_data["file_name"], user_id=user_id)
        parsed_data_added = parsed_data.model_dump()
        parsed_data_added["thread_id"] = thread_id
        parsed_data_added["user_id"] = user_id
        parsed_data_added_json = json.dumps(parsed_data_added)
        # remove ext from file_name
        name, ext = os.path.splitext(file_data["file_name"])
        file_name = f"{name}.json"
        async with aiofiles.open(f"data/{user_id}/parsed/{file_name}", "w") as f:
            await f.write(parsed_data_added_json)
        
        documents.documents.append(parsed_data)

    return documents