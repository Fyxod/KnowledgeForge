import asyncio
import os
import time
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from core.embeddings.embeddings import get_embedding_function
from core.models.document import Documents

print("Loading embedding model...")
embedding_function = get_embedding_function()
print("Embedding model loaded.")


def chunk_page_text(page_text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150
    )  # try different chunk sizes
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
        batch = chunk_data[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        batch_ids, batch_texts, batch_metadatas = zip(*batch)

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
        print(f"Upserted batch {batch_idx + 1} in {end_time - start_time:.2f} seconds")

    print(f"Saved {len(chunk_data)} chunks to Chroma for user {user_id}")
