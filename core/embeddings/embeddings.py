from langchain_huggingface import HuggingFaceEmbeddings


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
