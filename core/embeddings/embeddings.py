from langchain_huggingface import HuggingFaceEmbeddings


def get_embedding_function():
    return HuggingFaceEmbeddings(
        model_name="nomic-ai/nomic-embed-text-v1.5",
        model_kwargs={
            "device": "cpu",
            "trust_remote_code": True,
        },
        encode_kwargs={
            "normalize_embeddings": True,
        },
    )
