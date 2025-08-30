import asyncio
import os
import json
import aiofiles
import datetime
from typing import List
from core.llm.client import invoke_llm
from core.models.document import Documents
from core.llm.outputs import (
    GlobalSummarizerLLMOutput,
    SummarizerLLMOutputSingle,
)
from core.llm.prompts.summarizer_query import (
    global_summarization_prompt,
    summarize_documents_prompt,
)
import time
from app.socket_handler import sio
from core.mind_map import create_mind_map
from core.mind_map_global import create_mind_map_global
from core.database import db
from core.constants import SUMMARIZER_LLM


def build_summarizer_prompt(document):
    """
    Builds the summarizer prompt for a single document.
    """
    formatted_doc = {
        "document_id": document.id,
        "text": document.full_text.replace("\x00", " ").strip(),
    }
    return summarize_documents_prompt(
        document=str(formatted_doc),
    )


async def summarize_documents(parsed_data: Documents):
    """
    Asynchronously summarizes the parsed data in batches of up to 5 documents using the LLM.
    """
    print("Inside summarizer")
    parsed_dir = f"data/{parsed_data.user_id}/threads/{parsed_data.thread_id}/parsed"
    os.makedirs(parsed_dir, exist_ok=True)

    documents = parsed_data.documents

    async def process_document(i, document):
        prompt = build_summarizer_prompt(document)
        start_time = time.time()
        try:
            await sio.emit(
                f"{parsed_data.user_id}/progress",
                {"message": f"Summarizing {document.title}"},
            )

            result: SummarizerLLMOutputSingle | None = None
            for attempt in range(5):  # max 5 attempts
                try:
                    await sio.emit(
                        f"{parsed_data.user_id}/progress",
                        {
                            "message": f"Attempt {attempt + 1} of summarizing {document.title}"
                        },
                    )

                    result = await invoke_llm(
                        SUMMARIZER_LLM, SummarizerLLMOutputSingle, prompt
                    )
                    if result and result.summary and len(result.summary.split()) >= 5:
                        break
                    else:
                        print(
                            f"Document {i}: summary too short ({len(result.summary.split())} words). Retrying once..."
                        )
                except asyncio.TimeoutError:
                    print(f"Document {i}: timeout on attempt {attempt+1}")
                except Exception as e:
                    print(f"Document {i}: error on attempt {attempt+1} -> {e}")

            end_time = time.time()
            if result:
                await sio.emit(
                    f"{parsed_data.user_id}/progress",
                    {"message": f"Summary completed for {document.title}"},
                )
                print(f"Summary completed for document {i}")
                print(f"LLM response time: {end_time - start_time:.2f} seconds")
                print(f"Completed document {i} in {end_time - start_time:.2f} seconds")

                document.summary = result.summary
                print("Entering mind map creation ", i)
                asyncio.create_task(
                    create_mind_map(
                        document, parsed_data.user_id, parsed_data.thread_id
                    )
                )
                await sio.emit(
                    f"{parsed_data.user_id}/{parsed_data.thread_id}/summary",
                    {"document_id": document.id, "status": True},
                )
            else:
                print(f"Document {i}: Failed to get valid summary after retries.")
                await asyncio.sleep(2)  # wait 2 seconds before retry
        except asyncio.TimeoutError:
            print(f"Document {i} took longer than 120 seconds, skipping.")
            await asyncio.sleep(2)  # wait 2 seconds before retry
        except Exception as e:
            print(f"Error processing document {i}: {e}")
            print("Skipping this document")
            await asyncio.sleep(2)  # wait 2 seconds before retry
            await sio.emit(
                f"{parsed_data.user_id}/{parsed_data.thread_id}/summary",
                {"document_id": document.id, "status": False},
            )

    try:
        batch_size = 5
        total_docs = len(documents)
        for batch_start in range(0, total_docs, batch_size):
            batch = [
                (i, documents[i])
                for i in range(batch_start, min(batch_start + batch_size, total_docs))
            ]
            await asyncio.gather(*(process_document(i, doc) for i, doc in batch))

        for document in parsed_data.documents:
            document_dict = document.model_dump()
            document_dict["thread_id"] = parsed_data.thread_id
            document_dict["user_id"] = parsed_data.user_id
            document_json = json.dumps(document_dict, ensure_ascii=False)

            name, _ = os.path.splitext(document.file_name)
            json_file_path = os.path.join(parsed_dir, f"{name}.json")

            async with aiofiles.open(json_file_path, "w", encoding="utf-8") as f:
                await f.write(document_json)
        print("before global summarizer")
        asyncio.create_task(create_mind_map_global(parsed_data))
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
        await sio.emit(f"{user_id}/{thread_id}/global", {"status": False})
        return
    user_threads = user.get("threads", {})

    if thread_id not in user_threads:
        print(f"No thread found with ID {thread_id} for user {user_id}")
        await sio.emit(f"{user_id}/{thread_id}/global", {"status": False})
        return

    summaries = []
    thread_documents = user_threads.get(thread_id, {}).get("documents", [])
    if not thread_documents:
        print(f"No documents found in thread {thread_id} for user {user_id}")
        await sio.emit(f"{user_id}/{thread_id}/global", {"status": False})
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

        async with aiofiles.open(json_file_path, "r", encoding="utf-8") as f:
            content = await f.read()
        document_data = json.loads(content)

        if document_data.get("summary"):
            summaries.append(
                {"title": document_data["title"], "summary": document_data["summary"]}
            )

    if not summaries:
        print(f"No summaries found for thread {thread_id} for user {user_id}")
        await sio.emit(f"{user_id}/{thread_id}/global", {"status": False})
        return

    summary_prompt = global_summarization_prompt(
        summaries=summaries,
    )

    try:
        start_time = time.time()
        print("Starting global summarization...")
        result: GlobalSummarizerLLMOutput = await invoke_llm(
            SUMMARIZER_LLM, GlobalSummarizerLLMOutput, summary_prompt
        )

        end_time = time.time()
        print(
            f"Global summarization completed in LLM response time {end_time - start_time:.2f} seconds"
        )
        print(f"Global summary completed: ")
        # save the global summary to a json file
        global_summary_path = os.path.join(save_dir, "global_summary.json")

        result_dict = result.model_dump()

        async with aiofiles.open(global_summary_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(result_dict, indent=2, ensure_ascii=False))
        await sio.emit(f"{user_id}/{thread_id}/global", {"status": True})

        if result.title:
            await updateThread(user_id, thread_id, result.title)

    except Exception as e:
        print(f"Error during global summarization: {e}")


async def updateThread(user_id: str, thread_id: str, updated_title: str):
    print(f"[WebSocket] Updating thread: user_id={user_id}, thread_id={thread_id}, title={updated_title}")
    now = datetime.datetime.now(datetime.timezone.utc)
    db.users.update_one(
        {"userId": user_id},
        {
            "$set": {
                f"threads.{thread_id}.thread_name": updated_title,
                f"threads.{thread_id}.updatedAt": now
            }
        }
    )
    
    event_name = f"{user_id}/{thread_id}/thread_update"
    event_data = {
        "threadId": thread_id,
        "newTitle": updated_title
    }
    print(f"[WebSocket] Emitting event: {event_name} with data: {event_data}")
    
    await sio.emit(event_name, event_data)
    print(f"[WebSocket] Event emitted successfully!")
