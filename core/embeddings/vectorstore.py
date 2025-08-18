import asyncio
import os
import time
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from core.embeddings.embeddings import get_embedding_function
from core.models.document import Documents

embedding_function = get_embedding_function()


def chunk_page_text(page_text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50) # try different chunk sizes
    return splitter.split_text(page_text)


# Get Chroma vector store instance
def get_vectorstore(user_id: str, thread_id: str) -> Chroma:
    persist_path = os.path.join("data", user_id, "chroma")
    os.makedirs(persist_path, exist_ok=True)

    return Chroma(
        collection_name="user_docs",
        persist_directory=persist_path,
        embedding_function=embedding_function,
    )


import math

async def save_documents_to_store(docs: Documents, user_id: str, thread_id: str):
    print("inside save_documents_to_store")
    start_time = time.time()
    vectorstore = await asyncio.to_thread(get_vectorstore, user_id, thread_id)
    end_time = time.time()
    print(
        f"Initialized Chroma vector store in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    chunk_data = []

    # Chunking
    start_time = time.time()
    for doc in docs.documents:
        for page in doc.content:
            chunks = await asyncio.to_thread(chunk_page_text, page.text)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.id}_page{page.number}_chunk{i}"
                metadata = {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "document_id": doc.id,
                    "page_no": page.number,
                    "chunk_index": i,
                    "file_name": doc.file_name,
                    "title": doc.title,
                }
                chunk_data.append((chunk_id, chunk, metadata))
    end_time = time.time()
    print(
        f"Processed {len(chunk_data)} chunks in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    # Batch embedding and upsert
    batch_size = 5000  # Don't change this in any case
    total_batches = math.ceil(len(chunk_data) / batch_size)

    for batch_idx in range(total_batches):
        batch = chunk_data[batch_idx * batch_size: (batch_idx + 1) * batch_size]
        batch_ids, batch_texts, batch_metadatas = zip(*batch)

        print(f"Embedding batch {batch_idx + 1}/{total_batches} with {len(batch_ids)} chunks")
        start_time = time.time()
        embeddings = await asyncio.to_thread(
            vectorstore.embeddings.embed_documents, list(batch_texts)
        )
        end_time = time.time()
        print(
            f"Generated embeddings for batch {batch_idx + 1} in {end_time - start_time:.2f} seconds"
        )

        # Upsert to Chroma
        print(f"Upserting batch {batch_idx + 1} to Chroma")
        start_time = time.time()
        await asyncio.to_thread(
            vectorstore._collection.upsert,
            embeddings=embeddings,
            documents=list(batch_texts),
            metadatas=list(batch_metadatas),
            ids=list(batch_ids),
        )
        end_time = time.time()
        print(
            f"Upserted batch {batch_idx + 1} in {end_time - start_time:.2f} seconds"
        )

    print(f"Saved {len(chunk_data)} chunks to Chroma for user {user_id}")

# from typing import Any, Dict, List
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_core.prompts import (
#     ChatPromptTemplate,
#     HumanMessagePromptTemplate,
#     MessagesPlaceholder,
# )


# def main_prompt(
#     messages: list,
#     documents: str,
#     question: str,
#     summary: str,
#     search_queries_results: List[Dict[str, Any]],
# ) -> ChatPromptTemplate:
#     """
#     Builds the main prompt for the agent based on the current state.
#     """

#     messages_array = [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant that answers questions based on the provided documents. "
#                 # "Use the retrieved context to provide the most accurate, direct, and specific answer possible. "
#                 "Use the retrieved context to give the best possible answer. "
#                 "Extract and use as much relevant information as possible from the documents. "
#                 "If the question is answerable using the provided documents, provide a direct, specific and detailed answer using relevant details."
#                 "Only if the question truly cannot be answered using the documents and your own knowledge, then ask for clarification or suggest a web search. "
#                 "Do not default to asking for clarification if relevant information is available in the context."
#                 "\n\n"
#                 "You also have access to these tools if needed:\n"
#                 "- `answer`: Use this if you can directly answer the question.\n"
#                 "- `web_search`: Use this if you need more recent or external information not available in the documents.\n"
#                 "- `document_summarizer`: Use this if you need the summary of a specific document. You must provide the `document_id`.\n"
#                 "- `global_summarizer`: Use this if you need a collective summary of all the documents.\n\n"
#             )
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#         HumanMessagePromptTemplate.from_template(
#             "Here is the retrieved context according to the question:\n{documents}"
#         ),
#     ]
#     if summary:
#         messages.append(HumanMessage(f"{summary}\n\n"))

#     if search_queries_results:
#         messages.append(
#             HumanMessage(
#                 f"Here are the web search queries results:{search_queries_results}\n\n"
#             )
#         )

#     messages.append(HumanMessagePromptTemplate.from_template("{question}"))

#     prompt = ChatPromptTemplate.from_messages(messages_array)
#     return prompt.format_messages(
#         messages=messages,
#         documents=documents,
#         question=question,
#     )
