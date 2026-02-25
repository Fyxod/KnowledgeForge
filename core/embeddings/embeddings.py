from langchain_huggingface import HuggingFaceEmbeddings


def get_embedding_function():
    return HuggingFaceEmbeddings(
        model_name="nomic-ai/nomic-embed-text-v1.5",
        model_kwargs={
            "device": "cuda",
            "trust_remote_code": True,
        },
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": 128,
        },
        # nomic-embed-text-v1.5 requires task-specific prefixes for optimal embeddings.
        # query_instruction is prepended only to embed_query() calls (search-time),
        # NOT to embed_documents() calls (index-time — handled in vectorstore.py).
        query_instruction="search_query: ",
    )
