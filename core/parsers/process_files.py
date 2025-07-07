from core.schemas.document import Documents
from core.parsers.main_parser import extract_document

async def process_files(
    file_paths: list[str],
    user_id: str,
    thread_id: str,
) -> dict:
    """
    pass all the files to main parser and return the parsed data
    and save them in an array according to the Documents model,
    return the array
    """

    documents = Documents(documents=[], thread_id=thread_id, user_id=user_id)

    for file_path in file_paths:
        # Call the main parser for each file and append the result to the documents array
        parsed_data = await extract_document(file_path)
        documents.documents.append(parsed_data)

    return documents