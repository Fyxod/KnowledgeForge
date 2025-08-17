import asyncio
import os
import json
import aiofiles
from typing import List
from core.llm.client import invoke_llm
from core.models.document import Documents
from core.llm.outputs import SummarizerLLMOutput, GlobalSummarizerLLMOutput, SummarizerLLMOutputSingle
from core.llm.prompts.summarizer_query import multi_document_summarization_prompt, global_summarization_prompt, summarize_documents_prompt
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












def build_summarizer_prompt_batch(documents_batch: List):
    """
    Builds the summarizer prompt for a batch of up to 5 documents.
    """
    formatted_docs = [
        {"document_id": document.id, "text": document.full_text.replace("\x00", " ").strip()}
        for document in documents_batch
    ]

    return summarize_documents_prompt(
        document=formatted_docs,
    )


async def summarize_documents(parsed_data: Documents):
    """
    Asynchronously summarizes the parsed data in batches of up to 5 documents using the LLM.
    """
    print("Inside summarizer")
    parsed_dir = f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    documents = parsed_data.documents
    batch_size = 1

    def chunk_documents(documents: List, size: int):
        for i in range(0, len(documents), size):
            yield documents[i:i + size]

    try:
        for i, batch in enumerate(chunk_documents(documents, batch_size)):
            prompt = build_summarizer_prompt_batch(batch)

            # async with aiofiles.open(f"formatted_summarizer_prompt_batch_{i}.txt", "w", encoding="utf-8") as f:
            #     for msg in prompt:
            #         role = msg.__class__.__name__.replace("Message", "").upper()
            #         await f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

            start_time = time.time()
            try:
                result: SummarizerLLMOutputSingle | None = None
                for attempt in range(2):  # max 2 attempts
                    try:
                        result = await invoke_llm(SUMMARIZER_LLM, SummarizerLLMOutputSingle, prompt)
                        if result and result.summary and len(result.summary.split()) >= 5:
                            break
                        else:
                            print(f"Batch {i}: summary too short ({len(result.summary.split())} words). Retrying once...")
                    except asyncio.TimeoutError:
                        print(f"Batch {i}: timeout on attempt {attempt+1}")
                    except Exception as e:
                        print(f"Batch {i}: error on attempt {attempt+1} -> {e}")

                end_time = time.time()
                if result:
                    print(f"Summary result for batch {i}: ", result)
                    print(f"LLM response time: {end_time - start_time:.2f} seconds")
                    print(f"Completed batch {i} in {end_time - start_time:.2f} seconds")

                    summarized_document_id = result.document_id
                    for document_obj in parsed_data.documents:
                        if summarized_document_id == document_obj.id:
                            document_obj.summary = result.summary
                            break
                else:
                    print(f"Batch {i}: Failed to get valid summary after retries.")
                    await asyncio.sleep(2)  # wait 2 seconds before retry

            except asyncio.TimeoutError:
                print(f"Batch {i} took longer than 120 seconds, skipping.")
                await asyncio.sleep(2)  # wait 2 seconds before retry
                continue
            except Exception as e:
                print(f"Error processing batch {i}: {e}")
                print("Skipping this batch")
                await asyncio.sleep(2)  # wait 2 seconds before retry
                continue

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

    summary_prompt = global_summarization_prompt(
        summaries=summaries,
    )
    
    # async with aiofiles.open(f"global_summarizer_prompt.txt", "w", encoding="utf-8") as f:
    #     for msg in summary_prompt:
    #         role = msg.__class__.__name__.replace("Message", "").upper()
    #         await f.write(f"{role}:\n{msg.content}\n\n{'-'*40}\n\n")

    try:
        start_time = time.time()
        print("Starting global summarization...")
        result: GlobalSummarizerLLMOutput = await invoke_llm(SUMMARIZER_LLM, GlobalSummarizerLLMOutput, summary_prompt)

        end_time = time.time()
        print(f"Global summarization completed in LLM response time {end_time - start_time:.2f} seconds")
        print(f"Global summary result: ", result)
        # save the global summary to a json file
        global_summary_path = os.path.join(save_dir, "global_summary.json")
        async with aiofiles.open(global_summary_path, "w") as f:
            await f.write(json.dumps(result.model_dump(), indent=2))

    except Exception as e:
        print(f"Error during global summarization: {e}")
