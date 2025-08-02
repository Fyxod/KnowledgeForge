from core.embeddings.vectorstore import get_vectorstore


def get_user_retriever(user_id: str, thread_id: str, k: int = 5):
    vectorstore = get_vectorstore(user_id, thread_id=thread_id)
    
    # Define the search_kwargs with the corrected filter structure
    search_kwargs = {
        "k": k,
        "filter": {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"thread_id": {"$eq": thread_id}},
            ]
        },
    }

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    return retriever