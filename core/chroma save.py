import os
import torch
import asyncio
from typing import List
from pydantic import BaseModel, Field
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import time
from core.schemas.document import Documents

def chunk_page_text(page_text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
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

# Get Chroma vector store instance
def get_chroma_vectorstore(user_id: str) -> Chroma:
    persist_path = os.path.join("data", user_id, "chroma")
    # persist_path = os.path.join("data", "users", user_id, "chroma")
    os.makedirs(persist_path, exist_ok=True)

    collection_name = "user_docs"
    embedding_function = get_embedding_function()

    client = chromadb.PersistentClient(path=persist_path)
    
    existing_collections = [col.name for col in client.list_collections()]
    if collection_name in existing_collections:
        
        print(f"Loading existing Chroma collection for user {user_id}")
    else:
        print(f"Creating new Chroma collection for user {user_id}")

    return Chroma(
        collection_name=collection_name,
        persist_directory=persist_path,
        embedding_function=get_embedding_function()
    )

async def save_documents_to_chroma(docs: Documents, user_id: str, thread_id: str):
    start_time = time.time()
    vectorstore = await asyncio.to_thread(get_chroma_vectorstore, user_id)
    end_time = time.time()
    print(f"Initialized Chroma vector store in {end_time - start_time:.2f} seconds for user {user_id}")
    
    all_ids = []
    all_texts = []
    all_metadatas = []

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
    start_time = time.time()
    embeddings = await asyncio.to_thread(vectorstore.embeddings.embed_documents, all_texts)
    end_time = time.time()
    print(f"Generated embeddings for {len(all_texts)} chunks in {end_time - start_time:.2f} seconds for user {user_id}")

    # Upsert all chunks to Chroma
    start_time = time.time()
    print(f"Upserting {len(all_ids)} chunks to Chroma for user {user_id}")
    await asyncio.to_thread(vectorstore._collection.upsert,
        embeddings=embeddings,
        documents=all_texts,
        metadatas=all_metadatas,
        ids=all_ids
    )

    end_time = time.time()
    print(f"Upserted {len(all_ids)} chunks to Chroma in {end_time - start_time:.2f} seconds for user {user_id}")

    print(f"Saved {len(all_ids)} chunks to Chroma for user {user_id}")

def get_user_retriever(user_id: str, k: int = 5):
    vectorstore = get_chroma_vectorstore(user_id)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    return retriever
