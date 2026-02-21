from core.embeddings.vectorstore import get_vectorstore, search_bm25
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


def reciprocal_rank_fusion(
    result_lists: List[List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    RRF assigns a score to each document based on its rank in each list:
        score(d) = sum(1 / (k + rank_i)) for each list i that contains d

    Args:
        result_lists: List of ranked result lists (each is a list of dicts with metadata)
        k: RRF constant (default 60, standard in literature)

    Returns:
        Merged and deduplicated results sorted by RRF score
    """
    scores = {}
    doc_map = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list):
            # Create a unique key for deduplication
            doc_id = doc.get("metadata", {}).get("document_id", "")
            page_no = doc.get("metadata", {}).get("page_no", 0)
            chunk_idx = doc.get("metadata", {}).get("chunk_index", rank)
            key = f"{doc_id}_p{page_no}_c{chunk_idx}"

            rrf_score = 1.0 / (k + rank + 1)
            scores[key] = scores.get(key, 0) + rrf_score
            if key not in doc_map:
                doc_map[key] = doc

    # Sort by RRF score descending
    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for key in sorted_keys:
        doc = doc_map[key].copy()
        doc["rrf_score"] = scores[key]
        results.append(doc)

    return results


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
    2. Ensures diversity across documents using embedding-based MMR
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

    # Step 2: MMR with cosine similarity for diversity
    reranked_chunks = []
    selected_indices = set()

    # Sort by relevance score initially
    sorted_indices = sorted(
        range(len(chunks)),
        key=lambda i: chunks[i]["relevance_score"],
        reverse=True
    )

    # Pre-compute TF-IDF-like vectors for cosine similarity (lightweight)
    chunk_vectors = _compute_tfidf_vectors(chunks)

    # Select chunks using MMR
    for _ in range(min(top_k, len(chunks))):
        best_idx = None
        best_score = -float('inf')

        for idx in sorted_indices:
            if idx in selected_indices:
                continue

            # Relevance score
            relevance = chunks[idx]["relevance_score"]

            # Diversity penalty using cosine similarity
            diversity_penalty = 0.0
            if reranked_chunks:
                max_similarity = 0.0
                for sel_idx in selected_indices:
                    sim = _cosine_similarity(chunk_vectors[idx], chunk_vectors[sel_idx])
                    max_similarity = max(max_similarity, sim)
                diversity_penalty = max_similarity

            # MMR score: balance relevance and diversity
            mmr_score = (1 - diversity_lambda) * relevance - diversity_lambda * diversity_penalty

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected_indices.add(best_idx)
            reranked_chunks.append(chunks[best_idx])

    print(f"Re-ranking complete. Selected {len(reranked_chunks)} chunks.")

    # Step 3: Log document diversity
    doc_counts = {}
    for chunk in reranked_chunks:
        doc_id = chunk.get("metadata", {}).get("document_id", "unknown")
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

    print(f"Document distribution after re-ranking:")
    for doc_id, count in doc_counts.items():
        print(f"  Document {doc_id}: {count} chunks")

    return reranked_chunks


def _compute_tfidf_vectors(chunks: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """Compute simple TF-IDF-like word frequency vectors for cosine similarity."""
    from collections import Counter

    # Build vocabulary from all chunks
    all_words = set()
    chunk_word_counts = []
    for chunk in chunks:
        words = chunk.get("page_content", "").lower().split()
        word_counts = Counter(words)
        chunk_word_counts.append(word_counts)
        all_words.update(words)

    # Compute document frequency
    doc_freq = Counter()
    for wc in chunk_word_counts:
        for word in wc:
            doc_freq[word] += 1

    n_docs = len(chunks)
    vectors = []
    for wc in chunk_word_counts:
        vec = {}
        for word, count in wc.items():
            tf = count / max(sum(wc.values()), 1)
            idf = math.log((n_docs + 1) / (doc_freq[word] + 1))
            vec[word] = tf * idf
        vectors.append(vec)

    return vectors


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse TF-IDF vectors."""
    # Find common words
    common_words = set(vec_a.keys()) & set(vec_b.keys())
    if not common_words:
        return 0.0

    dot_product = sum(vec_a[w] * vec_b[w] for w in common_words)
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


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


async def hybrid_retrieve(
    user_id: str,
    thread_id: str,
    query: str,
    vector_k: int = 30,
    bm25_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval combining vector search (ChromaDB) and BM25 keyword search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both retrievers,
    providing both semantic understanding and keyword matching.

    Args:
        user_id: User identifier
        thread_id: Thread identifier
        query: The user's search query
        vector_k: Number of results from vector search
        bm25_k: Number of results from BM25 search

    Returns:
        Merged and deduplicated results sorted by RRF score
    """
    import asyncio

    # Run vector search and BM25 search in parallel
    vector_retriever = get_user_retriever(user_id, thread_id, k=vector_k)

    async def get_vector_results():
        docs = await vector_retriever.ainvoke(query)
        return [doc.model_dump() for doc in docs]

    async def get_bm25_results():
        return await asyncio.to_thread(search_bm25, user_id, thread_id, query, bm25_k)

    vector_results, bm25_results = await asyncio.gather(
        get_vector_results(),
        get_bm25_results(),
    )

    print(f"Hybrid search: {len(vector_results)} vector + {len(bm25_results)} BM25 results")

    # If BM25 returns no results, just use vector search
    if not bm25_results:
        return vector_results

    # Merge using Reciprocal Rank Fusion
    fused = reciprocal_rank_fusion([vector_results, bm25_results])
    print(f"RRF fusion produced {len(fused)} unique results")

    return fused


async def get_multi_document_retriever(
    user_id: str,
    thread_id: str,
    document_ids: List[str],
    query: str = "",
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
        query: The user query for semantic similarity search
        k_per_document: Minimum chunks to retrieve per document
        total_k: Maximum total chunks to return

    Returns:
        List of retrieved document chunks with metadata
    """
    if not document_ids:
        # Fallback to hybrid retrieval if no documents specified
        return await hybrid_retrieve(user_id, thread_id, query, vector_k=total_k)

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
            retrieved_docs = await retriever.ainvoke(query)
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
        additional_docs = await retriever.ainvoke(query)

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
    query: str = "",
    k: int = None,
    min_chunks_per_doc: int = 3,
    max_total_chunks: int = 50
) -> List[Dict[str, Any]]:
    """
    Get retriever for all documents in a thread with adaptive document diversity.
    Uses hybrid search (vector + BM25) for improved recall.

    This function uses an adaptive strategy that:
    1. Ensures minimum chunks per document (min_chunks_per_doc)
    2. Scales total chunks based on document count
    3. Respects maximum total chunks limit (max_total_chunks)
    4. Provides balanced representation across all documents

    Args:
        user_id: User identifier
        thread_id: Thread identifier
        query: The user query for semantic similarity search
        k: Total number of chunks to retrieve (None for adaptive)
        min_chunks_per_doc: Minimum chunks to retrieve per document
        max_total_chunks: Maximum total chunks to return

    Returns:
        List of retrieved document chunks with metadata
    """
    # Use hybrid retrieval (vector + BM25) for better recall
    retrieved_docs = await hybrid_retrieve(
        user_id, thread_id, query,
        vector_k=max_total_chunks * 2,
        bm25_k=max_total_chunks,
    )

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
        if num_documents <= 2:
            k = 20
        elif num_documents <= 5:
            k = 50
        elif num_documents <= 10:
            k = 100
        else:
            k = min(max_total_chunks, num_documents * 10)

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
