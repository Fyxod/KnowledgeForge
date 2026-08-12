from langchain_huggingface import HuggingFaceEmbeddings
import torch

from core.config import settings


def get_embedding_function():
    configured_device = settings.EMBEDDINGS_DEVICE
    if configured_device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = configured_device

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "EMBEDDINGS_DEVICE=cuda was requested, but CUDA is not available. "
            "Use EMBEDDINGS_DEVICE=auto or cpu for a CPU-only runtime."
        )

    return HuggingFaceEmbeddings(
        model_name="nomic-ai/nomic-embed-text-v1.5",
        model_kwargs={
            "device": device,
            "trust_remote_code": True,
        },
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": settings.EMBEDDING_BATCH_SIZE,
        },
        # nomic-embed-text-v1.5 requires task-specific prefixes for optimal embeddings.
        # "prompt" is passed to sentence_transformers.encode() and prepended to text.
        # query_encode_kwargs applies ONLY to embed_query() calls (search-time),
        # NOT to embed_documents() calls (index-time — handled in vectorstore.py).
        query_encode_kwargs={
            "prompt": "search_query: ",
        },
    )

