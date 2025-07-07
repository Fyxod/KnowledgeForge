import os
import torch
import asyncio
import pickle
import time
from typing import List
from pydantic import BaseModel, Field

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from core.schemas.document import Documents


def chunk_page_text(page_text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_text(page_text)


def get_embedding_function():
    print("PRINTING CUDA")
    print(torch.cuda)
    print(torch.cuda.is_available())
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2", # decide model, this just temp
        # model_name="NovaSearch/stella_en_400M_v5",
        model_kwargs={
            "device": "cpu",
            # "device": "cuda" if torch.cuda.is_available() else "cpu",
            "trust_remote_code": True
        },
    )

embedding_function = get_embedding_function()

# Load or initialize FAISS vector store
def get_vectorstore(user_id: str) -> FAISS:
    persist_path = os.path.join("data", user_id, "faiss")
    os.makedirs(persist_path, exist_ok=True)

    index_file = os.path.join(persist_path, "index.faiss")
    metadata_file = os.path.join(persist_path, "metadata.pkl")


    if os.path.exists(index_file) and os.path.exists(metadata_file):
        # Load FAISS index and metadata
        with open(metadata_file, "rb") as f:
            stored = pickle.load(f)
        faiss_index = FAISS.load_local(persist_path, embedding_function, allow_dangerous_deserialization=True)
        faiss_index.docstore._metadatas = stored["metadatas"]
        faiss_index.docstore._ids = stored["ids"]
        return faiss_index
    else:
        return FAISS.from_texts(["dummy"], embedding_function)


# Save FAISS index + metadata
# def save_faiss_vectorstore(faiss_index: FAISS, user_id: str):
#     persist_path = os.path.join("data", user_id, "faiss")
#     os.makedirs(persist_path, exist_ok=True)

#     faiss_index.save_local(persist_path)
#     metadata_file = os.path.join(persist_path, "metadata.pkl")
#     with open(metadata_file, "wb") as f:
#         pickle.dump({
#             "metadatas": faiss_index.docstore._metadatas,
#             "ids": faiss_index.docstore._ids,
#         }, f)

import os
import pickle
from langchain_community.vectorstores import FAISS
# Assuming FAISS is imported from langchain_community.vectorstores.FAISS if using newer versions.
# If you're using an older version, it might be from langchain.vectorstores.faiss

def save_faiss_vectorstore(faiss_index: FAISS, user_id: str):
    persist_path = os.path.join("data", user_id, "faiss")
    os.makedirs(persist_path, exist_ok=True)

    faiss_index.save_local(persist_path)

    all_metadatas = []
    all_ids = []
    
    # Corrected line: Use _dict instead of _docs
    for doc_id, doc in faiss_index.docstore._dict.items():
        all_ids.append(doc_id)
        all_metadatas.append(doc.metadata)

    metadata_file = os.path.join(persist_path, "metadata.pkl")
    with open(metadata_file, "wb") as f:
        pickle.dump({
            "metadatas": all_metadatas,
            "ids": all_ids,
        }, f)


async def save_documents_to_store(docs: Documents, user_id: str, thread_id: str):
    start_time = time.time()
    vectorstore = await asyncio.to_thread(get_vectorstore, user_id)
    end_time = time.time()
    print(f"Initialized FAISS vector store in {end_time - start_time:.2f} seconds for user {user_id}")

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
    print(f"Processed {len(all_ids)} chunks in {end_time - start_time:.2f} seconds for user {user_id}")

    # Embedding
    start_time = time.time()
    embeddings = await asyncio.to_thread(vectorstore.embedding_function.embed_documents, all_texts)
    end_time = time.time()
    print(f"Generated embeddings for {len(all_texts)} chunks in {end_time - start_time:.2f} seconds for user {user_id}")

    # Build new or add to existing FAISS vectorstore
    start_time = time.time()
    print(f"Upserting {len(all_ids)} chunks to FAISS for user {user_id}")
    text_embeddings = list(zip(all_texts, embeddings))

    await asyncio.to_thread(vectorstore.add_embeddings, text_embeddings, all_metadatas, all_ids)
    end_time = time.time()
    print(f"Upserted {len(all_ids)} chunks to FAISS in {end_time - start_time:.2f} seconds for user {user_id}")

    await asyncio.to_thread(save_faiss_vectorstore, vectorstore, user_id)
    print(f"Saved {len(all_ids)} chunks to FAISS for user {user_id}")


def get_user_retriever(user_id: str, k: int = 5):
    vectorstore = get_vectorstore(user_id)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    return retriever
