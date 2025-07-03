import asyncio
from typing import List
from pydantic import BaseModel, Field
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import torch

class Page(BaseModel):
    page_no: int
    text: str
    images: List[str] = Field(default_factory=list)

class Document(BaseModel):
    id: str
    type: str
    file_name: str
    content: List[Page] = Field(default_factory=list)
    title: str

class Documents(BaseModel):
    documents: List[Document] = Field(default_factory=list)
    thread_id: str
    user_id: str

def chunk_page_text(page_text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    return splitter.split_text(page_text)

def get_embedding_function():
    return HuggingFaceEmbeddings(
        model_name="TaylorAI/StellaBase-en-v2",
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"}
    )

# Get Chroma vector store instance
def get_chroma_vectorstore(user_id: str) -> Chroma:
    persist_path = os.path.join("data", "users", user_id, "chroma")
    os.makedirs(persist_path, exist_ok=True)

    return Chroma(
        collection_name="user_docs",
        persist_directory=persist_path,
        embedding_function=get_embedding_function()
    )

async def save_documents_to_chroma(docs: Documents, user_id: str, thread_id: str):
    vectorstore = await asyncio.to_thread(get_chroma_vectorstore, user_id)

    all_ids = []
    all_texts = []
    all_metadatas = []

    for doc in docs.documents:
        for page in doc.content:
            chunks = await asyncio.to_thread(chunk_page_text, page.text)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.id}_page{page.page_no}_chunk{i}"
                metadata = {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "document_id": doc.id,
                    "page_no": page.page_no,
                    "chunk_index": i,
                    "file_name": doc.file_name,
                    "doc_title": doc.title,
                }
                all_ids.append(chunk_id)
                all_texts.append(chunk)
                all_metadatas.append(metadata)

    embeddings = await asyncio.to_thread(vectorstore._embedding.embed_documents, all_texts)

    await asyncio.to_thread(vectorstore._collection.upsert,
        embeddings=embeddings,
        documents=all_texts,
        metadatas=all_metadatas,
        ids=all_ids
    )

    print(f"Saved {len(all_ids)} chunks to Chroma for user {user_id}")

def get_user_retriever(user_id: str, k: int = 5):
    vectorstore = get_chroma_vectorstore(user_id)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    return retriever
