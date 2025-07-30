import torch
from langchain_huggingface import HuggingFaceEmbeddings
import requests
import httpx
from typing import List
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field
from core.config import settings

def get_embedding_function():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",  # decide model, this just temp
        # model_name="NovaSearch/stella_en_400M_v5",
        model_kwargs={
            "device": "cpu",
            # "device": "cuda" if torch.cuda.is_available() else "cpu",
            "trust_remote_code": True,
        },
    )
    
#     return RemoteEmbeddings(
#         api_url=f"{settings.LLM_URL}"  # replace with your actual API URL
#     )


# class RemoteEmbeddings(BaseModel, Embeddings):
#     """
#     LangChain-compatible remote embedding class.

#     Calls a remote HTTP API that returns text embeddings.
#     """

#     api_url: str = Field(..., description="The URL of the remote embedding API. Example: http://your-server:8000")

#     def embed_documents(self, texts: List[str]) -> List[List[float]]:
#         """Embed multiple texts via a remote API."""
#         response = requests.post(f"{self.api_url}/embed", json={"texts": texts})
#         response.raise_for_status()
#         return response.json()["embeddings"]

#     def embed_query(self, text: str) -> List[float]:
#         """Embed a single query text via a remote API."""
#         return self.embed_documents([text])[0]

#     async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
#         """Async version of embed_documents."""
#         async with httpx.AsyncClient() as client:
#             response = await client.post(f"{self.api_url}/embed", json={"texts": texts})
#             response.raise_for_status()
#             return response.json()["embeddings"]

#     async def aembed_query(self, text: str) -> List[float]:
#         """Async version of embed_query."""
#         embeddings = await self.aembed_documents([text])
#         return embeddings[0]