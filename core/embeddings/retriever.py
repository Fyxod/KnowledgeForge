from core.embeddings.vectorstore import get_vectorstore


def get_user_retriever(
    user_id: str, thread_id: str, document_id: str = None, k: int = 5
):
    vectorstore = get_vectorstore(user_id, thread_id=thread_id)

    filter_conditions = []
    if user_id is not None:
        filter_conditions.append({"user_id": {"$eq": user_id}})
    if thread_id is not None:
        filter_conditions.append({"thread_id": {"$eq": thread_id}})
    if document_id is not None:
        filter_conditions.append({"document_id": {"$eq": document_id}})
    search_kwargs = {
        "k": k,
        "filter": {"$and": filter_conditions},
    }

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    return retriever
