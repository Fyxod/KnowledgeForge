import os
import json
import aiofiles
from typing import List
from core.llm.client import get_llm
from core.models.document import Documents
from core.llm.outputs import SummarizerLLMOutput, GlobalSummarizerLLMOutput
from core.llm.prompts.summarizer_query import multi_document_summarization_prompt, global_summarization_prompt
from langchain_core.prompts import ChatPromptTemplate
import time
from core.database import db
from core.constants import SUMMARIZER_LLM

# def summarize_documents(parsed_data: Documents):
#     """
#     Summarizes the parsed data using the LLM.
#     """
#     structured_llm = llm.with_structured_output(SummarizerLLMOutput)
#     prompt = build_summarizer_prompt(parsed_data)
#     with open("formatted_summarizer_prompt.txt", "w", encoding="utf-8") as f:
#         for msg in prompt:
#             role = msg.__class__.__name__.replace("Message", "").upper()
#             f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

#     try:
#         result: SummarizerLLMOutput = structured_llm.invoke(prompt)
#         print("Summary result: ", result)
#         for document in result.summaries:
#             parsed_data.documents[f"{document.document_id}"].summary = document.summary

#         return parsed_data

#     except Exception as e:
#         print(f"Error during summarization: {e}")
#         return parsed_data


# def build_summarizer_prompt(parsed_data: Documents) -> ChatPromptTemplate:
#     """
#     Builds the main prompt for the agent based on the current state.
#     """
#     documents = []
#     for document in parsed_data.documents:
#         documents.append({"document_id": document.id, "text": document.full_text})

#     return multi_document_summarization_prompt.format_messages(
#         documents=documents,
#     )












def build_summarizer_prompt_batch(documents_batch: List) -> ChatPromptTemplate:
    """
    Builds the summarizer prompt for a batch of up to 5 documents.
    """
    formatted_docs = [
        {"document_id": document.id, "text": document.full_text}
        for document in documents_batch
    ]

    return multi_document_summarization_prompt.format_messages(
        documents=formatted_docs,
    )


async def summarize_documents(parsed_data: Documents):
    """
    Asynchronously summarizes the parsed data in batches of up to 5 documents using the LLM.
    """
    print("Inside summarizer")
    parsed_dir = f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    llm = get_llm(SUMMARIZER_LLM)
    structured_llm = llm.with_structured_output(SummarizerLLMOutput)

    documents = parsed_data.documents
    batch_size = 5

    def chunk_documents(documents: List, size: int):
        for i in range(0, len(documents), size):
            yield documents[i:i + size]

    try:
        for i, batch in enumerate(chunk_documents(documents, batch_size)):
            prompt = build_summarizer_prompt_batch(batch)

            async with aiofiles.open(f"formatted_summarizer_prompt_batch_{i}.txt", "w", encoding="utf-8") as f:
                for msg in prompt:
                    role = msg.__class__.__name__.replace("Message", "").upper()
                    await f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

            start_time = time.time()
            result: SummarizerLLMOutput = await structured_llm.ainvoke(prompt)
            print(f"Summary result for batch {i}: ", result)
            end_time = time.time()
            print(f"LLM response time: {end_time - start_time:.2f} seconds")
            print(f"Completed batch {i} in {end_time - start_time:.2f} seconds")
            
            for document in result.summaries:
                for document_obj in parsed_data.documents:
                    if document.document_id == document_obj.id:
                        document_obj.summary = document.summary
                        break

        for document in parsed_data.documents:
            document_dict = document.model_dump()
            document_dict["thread_id"] = parsed_data.thread_id
            document_dict["user_id"] = parsed_data.user_id
            document_json = json.dumps(document_dict)

            name, _ = os.path.splitext(document.file_name)
            json_file_path = os.path.join(parsed_dir, f"{name}.json")

            async with aiofiles.open(json_file_path, "w") as f:
                await f.write(document_json)
        print("before global summarizer")
        await global_summarizer(parsed_data.user_id, parsed_data.thread_id)

    except Exception as e:
        print(f"Error during summarization: {e}")
        
async def global_summarizer(user_id: str, thread_id: str):
    """
    Asynchronously summarizes all documents for a user in a specific thread.
    """
    save_dir = f"data/{user_id}/threads/{thread_id}"
    parsed_dir = f"data/{user_id}/threads/{thread_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    user = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
    if not user:
        print(f"User with ID {user_id} not found")
        return
    user_threads = user.get("threads", {})
    
    if(thread_id not in user_threads):
        print(f"No thread found with ID {thread_id} for user {user_id}")
        return

    summaries = []
    thread_documents = user_threads.get(thread_id, {}).get("documents", [])
    if not thread_documents:
        print(f"No documents found in thread {thread_id} for user {user_id}")
        return

    for document in thread_documents:
        file_name = document["file_name"]
        if not file_name:
            print(f"Document {document['id']} has no file name, skipping...")
            continue

        name, _ = os.path.splitext(file_name)
        json_file_path = os.path.join(parsed_dir, f"{name}.json")

        if not os.path.exists(json_file_path):
            print(f"Parsed file {json_file_path} does not exist, skipping...")
            continue
        
        async with aiofiles.open(json_file_path, "r") as f:
            content = await f.read()
        document_data = json.loads(content)
        if document_data.get("summary"):
            summaries.append({
                "title": document_data["title"],
                "summary": document_data["summary"]
            })

    if not summaries:
        print(f"No summaries found for thread {thread_id} for user {user_id}")
        return

    summary_prompt = global_summarization_prompt.format_messages(
        summaries=summaries,
    )
    
    async with aiofiles.open(f"global_summarizer_prompt.txt", "w", encoding="utf-8") as f:
        for msg in summary_prompt:
            role = msg.__class__.__name__.replace("Message", "").upper()
            await f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

    llm = get_llm(SUMMARIZER_LLM)
    structured_llm = llm.with_structured_output(GlobalSummarizerLLMOutput)
    try:
        start_time = time.time()
        print("Starting global summarization...")
        result: GlobalSummarizerLLMOutput = await structured_llm.ainvoke(summary_prompt)
        end_time = time.time()
        print(f"Global summarization completed in LLM response time {end_time - start_time:.2f} seconds")
        print(f"Global summary result: ", result)
        # save the global summary to a json file
        global_summary_path = os.path.join(save_dir, "global_summary.json")
        async with aiofiles.open(global_summary_path, "w") as f:
            await f.write(json.dumps(result.model_dump(), indent=2))

    except Exception as e:
        print(f"Error during global summarization: {e}")
