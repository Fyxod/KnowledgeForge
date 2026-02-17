from core.embeddings.vectorstore import get_vectorstore
from typing import List, Dict, Any
import math
from sentence_transformers import CrossEncoder
import numpy as np

# Initialize cross-encoder for re-ranking (lazy loading)
_cross_encoder = None


def get_cross_encoder():
    """Lazy load the cross-encoder model."""
    global _cross_encoder
    if _cross_encoder is None:
        print("Loading cross-encoder model for re-ranking...")
        _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        print("Cross-encoder model loaded.")
    return _cross_encoder


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = None,
    diversity_lambda: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Re-rank retrieved chunks using cross-encoder and ensure diversity.

    This function:
    1. Re-ranks chunks based on query relevance using cross-encoder
    2. Ensures diversity across documents (MMR - Maximal Marginal Relevance)
    3. Removes redundant chunks
    4. Balances representation across documents

    Args:
        query: The user's query
        chunks: List of retrieved chunks with metadata
        top_k: Number of top chunks to return (None for all)
        diversity_lambda: Trade-off between relevance and diversity (0-1)
                         Higher values prioritize diversity

    Returns:
        Re-ranked and diversified list of chunks
    """
    if not chunks:
        return []

    if top_k is None:
        top_k = len(chunks)

    print(f"Re-ranking {len(chunks)} chunks for query...")

    # Step 1: Cross-encoder re-ranking for relevance
    try:
        cross_encoder = get_cross_encoder()

        # Prepare query-chunk pairs
        pairs = [(query, chunk.get("page_content", "")) for chunk in chunks]

        # Get relevance scores
        scores = cross_encoder.predict(pairs)

        # Add scores to chunks
        for i, chunk in enumerate(chunks):
            chunk["relevance_score"] = float(scores[i])

        print(f"Cross-encoder re-ranking completed.")

    except Exception as e:
        print(f"Cross-encoder re-ranking failed: {e}. Using original order.")
        # Fallback: use original order with default scores
        for i, chunk in enumerate(chunks):
            chunk["relevance_score"] = 1.0 - (i / len(chunks))  # Decreasing scores

    # Step 2: Maximal Marginal Relevance (MMR) for diversity
    reranked_chunks = []
    selected_indices = set()

    # Sort by relevance score initially
    sorted_indices = sorted(
        range(len(chunks)),
        key=lambda i: chunks[i]["relevance_score"],
        reverse=True
    )

    # Select chunks using MMR
    for _ in range(min(top_k, len(chunks))):
        best_idx = None
        best_score = -float('inf')

        for idx in sorted_indices:
            if idx in selected_indices:
                continue

            # Relevance score
            relevance = chunks[idx]["relevance_score"]

            # Diversity penalty (similarity to already selected chunks)
            diversity_penalty = 0.0
            if reranked_chunks:
                for selected_chunk in reranked_chunks:
                    # Simple similarity based on document_id and content overlap
                    doc_similarity = 1.0 if chunks[idx].get("metadata", {}).get("document_id") == selected_chunk.get("metadata", {}).get("document_id") else 0.0

                    # Content similarity (Jaccard similarity on words)
                    content1 = set(chunks[idx].get("page_content", "").lower().split())
                    content2 = set(selected_chunk.get("page_content", "").lower().split())

                    if content1 and content2:
                        content_similarity = len(content1 & content2) / len(content1 | content2)
                    else:
                        content_similarity = 0.0

                    diversity_penalty += 0.5 * doc_similarity + 0.5 * content_similarity

            # MMR score
            mmr_score = (1 - diversity_lambda) * relevance - diversity_lambda * diversity_penalty

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected_indices.add(best_idx)
            reranked_chunks.append(chunks[best_idx])

    print(f"Re-ranking complete. Selected {len(reranked_chunks)} chunks.")

    # Step 3: Ensure document diversity
    # Count chunks per document
    doc_counts = {}
    for chunk in reranked_chunks:
        doc_id = chunk.get("metadata", {}).get("document_id", "unknown")
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

    print(f"Document distribution after re-ranking:")
    for doc_id, count in doc_counts.items():
        print(f"  Document {doc_id}: {count} chunks")

    return reranked_chunks


def get_user_retriever(
    user_id: str,
    thread_id: str,
    document_id: str = None,
    k: int = 5
):
    """
    Get a retriever for a specific user, thread, and optionally document.

    Args:
        user_id: User identifier
        thread_id: Thread identifier
        document_id: Optional document identifier to filter by
        k: Number of chunks to retrieve

    Returns:
        LangChain retriever object
    """
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


async def get_multi_document_retriever(
    user_id: str,
    thread_id: str,
    document_ids: List[str],
    k_per_document: int = 6,
    total_k: int = 12
) -> List[Dict[str, Any]]:
    """
    Robust retrieval for multiple documents with balanced representation.

    This function ensures that:
    1. Each document gets a minimum number of chunks (k_per_document)
    2. Total chunks don't exceed total_k
    3. Documents are represented proportionally

    Args:
        user_id: User identifier
        thread_id: Thread identifier
        document_ids: List of document IDs to retrieve from
        k_per_document: Minimum chunks to retrieve per document
        total_k: Maximum total chunks to return

    Returns:
        List of retrieved document chunks with metadata
    """
    if not document_ids:
        # Fallback to thread-level retrieval if no documents specified
        retriever = get_user_retriever(user_id, thread_id, k=total_k)
        retrieved_docs = await retriever.ainvoke("")
        return [doc.model_dump() for doc in retrieved_docs]

    num_documents = len(document_ids)

    # Calculate chunks per document
    # Strategy: Ensure minimum chunks per document, then distribute remaining
    if num_documents == 1:
        chunks_per_doc = total_k
    else:
        # Calculate balanced distribution
        chunks_per_doc = min(
            k_per_document,
            math.ceil(total_k / num_documents)
        )

    print(f"Retrieving {chunks_per_doc} chunks per document from {num_documents} documents")

    all_retrieved_docs = []

    # Retrieve chunks from each document separately
    for doc_id in document_ids:
        retriever = get_user_retriever(
            user_id,
            thread_id,
            document_id=doc_id,
            k=chunks_per_doc
        )

        try:
            retrieved_docs = await retriever.ainvoke("")
            all_retrieved_docs.extend([doc.model_dump() for doc in retrieved_docs])
            print(f"Retrieved {len(retrieved_docs)} chunks from document {doc_id}")
        except Exception as e:
            print(f"Error retrieving from document {doc_id}: {e}")
            continue

    # If we have fewer chunks than total_k, try to get more from all documents
    if len(all_retrieved_docs) < total_k:
        additional_chunks_needed = total_k - len(all_retrieved_docs)
        print(f"Retrieving {additional_chunks_needed} additional chunks from all documents")

        # Get additional chunks without document filter
        retriever = get_user_retriever(user_id, thread_id, k=additional_chunks_needed)
        additional_docs = await retriever.ainvoke("")

        # Filter out documents we already have enough chunks from
        existing_doc_ids = set(doc.get("metadata", {}).get("document_id") for doc in all_retrieved_docs)
        for doc in additional_docs:
            doc_data = doc.model_dump()
            doc_id = doc_data.get("metadata", {}).get("document_id")
            if doc_id not in existing_doc_ids or len(all_retrieved_docs) < total_k:
                all_retrieved_docs.append(doc_data)

    # Ensure we don't exceed total_k
    all_retrieved_docs = all_retrieved_docs[:total_k]

    print(f"Total retrieved chunks: {len(all_retrieved_docs)}")
    return all_retrieved_docs


async def get_thread_documents_retriever(
    user_id: str,
    thread_id: str,
    k: int = None,
    min_chunks_per_doc: int = 3,
    max_total_chunks: int = 50
) -> List[Dict[str, Any]]:
    """
    Get retriever for all documents in a thread with adaptive document diversity.

    This function uses an adaptive strategy that:
    1. Ensures minimum chunks per document (min_chunks_per_doc)
    2. Scales total chunks based on document count
    3. Respects maximum total chunks limit (max_total_chunks)
    4. Provides balanced representation across all documents

    Adaptive Strategy:
    - 1-2 documents: 12 chunks total (6 per doc)
    - 3-5 documents: 20 chunks total (4-6 per doc)
    - 6-10 documents: 30 chunks total (3-5 per doc)
    - 10+ documents: 40-50 chunks total (3-5 per doc)

    Args:
        user_id: User identifier
        thread_id: Thread identifier
        k: Total number of chunks to retrieve (None for adaptive)
        min_chunks_per_doc: Minimum chunks to retrieve per document
        max_total_chunks: Maximum total chunks to return

    Returns:
        List of retrieved document chunks with metadata
    """
    # First, get all chunks to understand document distribution
    retriever = get_user_retriever(user_id, thread_id, k=max_total_chunks * 2)
    retrieved_docs = await retriever.ainvoke("")
    retrieved_docs = [doc.model_dump() for doc in retrieved_docs]

    # Group by document_id
    docs_by_document: Dict[str, List[Dict[str, Any]]] = {}
    for doc in retrieved_docs:
        doc_id = doc.get("metadata", {}).get("document_id", "unknown")
        if doc_id not in docs_by_document:
            docs_by_document[doc_id] = []
        docs_by_document[doc_id].append(doc)

    num_documents = len(docs_by_document)
    if num_documents == 0:
        return []

    # Adaptive k calculation based on document count
    if k is None:
        # Calculate adaptive k based on document count
        if num_documents <= 2:
            k = 20  # 10 chunks per doc
        elif num_documents <= 5:
            k = 50  # 10 chunks per doc
        elif num_documents <= 10:
            k = 100  # 10 chunks per doc
        else:
            k = min(max_total_chunks, num_documents * 10)  # 10 chunks per doc, max 100

    print(f"Adaptive k={k} for {num_documents} documents")

    # Calculate chunks per document
    chunks_per_doc = math.ceil(k / num_documents)

    # Ensure minimum chunks per document
    chunks_per_doc = max(chunks_per_doc, min_chunks_per_doc)

    # Recalculate total k based on chunks per doc
    adaptive_k = min(chunks_per_doc * num_documents, max_total_chunks)

    print(f"Retrieving {chunks_per_doc} chunks per document from {num_documents} documents (total: {adaptive_k})")

    # Select chunks from each document
    balanced_docs = []
    for doc_id, docs in docs_by_document.items():
        # Take top chunks_per_doc from this document
        balanced_docs.extend(docs[:chunks_per_doc])

    # Ensure we don't exceed adaptive_k
    balanced_docs = balanced_docs[:adaptive_k]

    print(f"Final retrieved: {len(balanced_docs)} chunks from {num_documents} documents")
    for doc_id, docs in docs_by_document.items():
        count = sum(1 for doc in balanced_docs if doc.get("metadata", {}).get("document_id") == doc_id)
        print(f"  Document {doc_id}: {count} chunks")

    return balanced_docs
