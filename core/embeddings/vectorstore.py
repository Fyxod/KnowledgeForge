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
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_text(page_text)


# Get Chroma vector store instance
def get_vectorstore(user_id: str) -> Chroma:
    persist_path = os.path.join("data", user_id, "chroma")
    os.makedirs(persist_path, exist_ok=True)

    return Chroma(
        collection_name="user_docs",
        persist_directory=persist_path,
        embedding_function=embedding_function,
    )


async def save_documents_to_store(docs: Documents, user_id: str, thread_id: str):
    start_time = time.time()
    vectorstore = await asyncio.to_thread(get_vectorstore, user_id)
    end_time = time.time()
    print(
        f"Initialized Chroma vector store in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    all_ids = []
    all_texts = []
    all_metadatas = []

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
                    "doc_title": doc.title,
                }
                all_ids.append(chunk_id)
                all_texts.append(chunk)
                all_metadatas.append(metadata)
    end_time = time.time()
    print(
        f"Processed {len(all_ids)} chunks in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    # Embedding
    start_time = time.time()
    embeddings = await asyncio.to_thread(
        vectorstore.embeddings.embed_documents, all_texts
    )
    end_time = time.time()
    print(
        f"Generated embeddings for {len(all_texts)} chunks in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    # Upsert to Chroma
    start_time = time.time()
    print(f"Upserting {len(all_ids)} chunks to Chroma for user {user_id}")
    await asyncio.to_thread(
        vectorstore._collection.upsert,
        embeddings=embeddings,
        documents=all_texts,
        metadatas=all_metadatas,
        ids=all_ids,
    )
    end_time = time.time()
    print(
        f"Upserted {len(all_ids)} chunks to Chroma in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    print(f"Saved {len(all_ids)} chunks to Chroma for user {user_id}")
