import asyncio
import os
import time
import pickle
import math
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from core.embeddings.embeddings import get_embedding_function
from core.models.document import Documents

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    nltk.download("punkt_tab", quiet=True)
    _HAS_NLTK = True
except ImportError:
    _HAS_NLTK = False

print("Loading embedding model...")
embedding_function = get_embedding_function()
print("Embedding model loaded.")

# Improved chunking parameters (512 chars, ~20% overlap)
CHUNK_SIZE = 512
CHUNK_OVERLAP = 100


def chunk_page_text(page_text: str) -> List[str]:
    """
    Split page text into chunks with sentence-boundary awareness.
    Falls back to RecursiveCharacterTextSplitter for robustness.
    """
    if _HAS_NLTK:
        # Sentence-boundary aware: split into sentences first, then merge into chunks
        sentences = sent_tokenize(page_text)
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > CHUNK_SIZE and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap from the end of the last chunk
                overlap_text = current_chunk[-CHUNK_OVERLAP:] if len(current_chunk) > CHUNK_OVERLAP else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk = (current_chunk + " " + sentence).strip()
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If NLTK produces no output (edge case), fall back
        if chunks:
            return chunks

    # Fallback: RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(page_text)


# Expected embedding dimension for the current model
_EXPECTED_DIM = None


def _get_expected_dim() -> int:
    """Get the expected embedding dimension from the current model (cached)."""
    global _EXPECTED_DIM
    if _EXPECTED_DIM is None:
        test_emb = embedding_function.embed_query("test")
        _EXPECTED_DIM = len(test_emb)
        print(f"Embedding model dimension: {_EXPECTED_DIM}")
    return _EXPECTED_DIM


def _check_and_migrate_chroma(persist_path: str, user_id: str):
    """
    Check if existing ChromaDB data has mismatched embedding dimensions.
    If so, delete the entire persist directory to force re-creation.
    Uses filesystem-level cleanup to avoid dual-client conflicts.
    """
    import shutil
    import chromadb

    try:
        client = chromadb.PersistentClient(path=persist_path)
        try:
            collection = client.get_collection("user_docs")
            if collection.count() > 0:
                sample = collection.get(limit=1, include=["embeddings"])
                if sample and sample.get("embeddings") and len(sample["embeddings"]) > 0:
                    existing_dim = len(sample["embeddings"][0])
                    expected_dim = _get_expected_dim()
                    if existing_dim != expected_dim:
                        print(
                            f"[MIGRATION] Embedding dimension changed: {existing_dim} → {expected_dim}. "
                            f"Resetting ChromaDB for user {user_id}."
                        )
                        # Close the client, then nuke the directory
                        del client
                        shutil.rmtree(persist_path, ignore_errors=True)
                        os.makedirs(persist_path, exist_ok=True)
                        return
        except ValueError:
            # Collection doesn't exist, that's fine
            pass
        # Clean up client reference so LangChain can create its own
        del client
    except Exception as e:
        print(f"[MIGRATION CHECK] Error checking dimensions: {e}")
        # If anything goes wrong, nuke and recreate to be safe
        import shutil
        shutil.rmtree(persist_path, ignore_errors=True)
        os.makedirs(persist_path, exist_ok=True)


# Get Chroma vector store instance (with auto-migration for dimension changes)
def get_vectorstore(user_id: str, thread_id: str) -> Chroma:
    persist_path = os.path.join("data", user_id, "chroma")
    os.makedirs(persist_path, exist_ok=True)

    # Check for dimension mismatch before creating the LangChain Chroma wrapper
    _check_and_migrate_chroma(persist_path, user_id)

    return Chroma(
        collection_name="user_docs",
        persist_directory=persist_path,
        embedding_function=embedding_function,
    )


def _get_bm25_path(user_id: str, thread_id: str) -> str:
    """Get path for BM25 index storage."""
    bm25_dir = os.path.join("data", user_id, "bm25")
    os.makedirs(bm25_dir, exist_ok=True)
    return os.path.join(bm25_dir, f"{thread_id}.pkl")


def _build_and_save_bm25(chunk_data: list, user_id: str, thread_id: str):
    """Build and persist a BM25 index from chunk data."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("rank_bm25 not installed, skipping BM25 index creation.")
        return

    # Tokenize documents for BM25
    tokenized_docs = [text.lower().split() for (_, text, _) in chunk_data]
    bm25 = BM25Okapi(tokenized_docs)

    bm25_data = {
        "bm25": bm25,
        "chunk_ids": [cid for (cid, _, _) in chunk_data],
        "chunk_texts": [text for (_, text, _) in chunk_data],
        "chunk_metadatas": [meta for (_, _, meta) in chunk_data],
    }

    bm25_path = _get_bm25_path(user_id, thread_id)
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25_data, f)
    print(f"BM25 index saved to {bm25_path} ({len(chunk_data)} documents)")


def load_bm25(user_id: str, thread_id: str):
    """Load BM25 index from disk. Returns None if not found."""
    bm25_path = _get_bm25_path(user_id, thread_id)
    if not os.path.exists(bm25_path):
        return None
    with open(bm25_path, "rb") as f:
        return pickle.load(f)


def search_bm25(user_id: str, thread_id: str, query: str, top_k: int = 20):
    """Search the BM25 index for the given query."""
    bm25_data = load_bm25(user_id, thread_id)
    if bm25_data is None:
        return []

    tokenized_query = query.lower().split()
    scores = bm25_data["bm25"].get_scores(tokenized_query)

    # Get top_k indices sorted by score
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # Only include results with positive BM25 score
            results.append({
                "page_content": bm25_data["chunk_texts"][idx],
                "metadata": bm25_data["chunk_metadatas"][idx],
                "bm25_score": float(scores[idx]),
            })
    return results


async def save_documents_to_store(docs: Documents, user_id: str, thread_id: str):
    start_time = time.time()
    vectorstore = await asyncio.to_thread(get_vectorstore, user_id, thread_id)
    end_time = time.time()
    print(
        f"Initialized Chroma vector store in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    chunk_data = []

    # Chunking with contextual enrichment
    start_time = time.time()
    for doc in docs.documents:
        for page in doc.content:
            chunks = await asyncio.to_thread(chunk_page_text, page.text)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.id}_page{page.number}_chunk{i}"

                # Contextual enrichment: prepend title + page for better embeddings
                enriched_chunk = f"Document: {doc.title}\nPage {page.number}\n\n{chunk}"

                metadata = {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "document_id": doc.id,
                    "page_no": page.number,
                    "chunk_index": i,
                    "file_name": doc.file_name,
                    "title": doc.title,
                }
                chunk_data.append((chunk_id, enriched_chunk, metadata))
    end_time = time.time()
    print(
        f"Processed {len(chunk_data)} chunks in {end_time - start_time:.2f} seconds for user {user_id}"
    )

    # Build and save BM25 index for hybrid search
    await asyncio.to_thread(_build_and_save_bm25, chunk_data, user_id, thread_id)

    # Batch embedding and upsert
    batch_size = 5000  # Don't change this in any case
    total_batches = math.ceil(len(chunk_data) / batch_size)

    for batch_idx in range(total_batches):
        batch = chunk_data[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        batch_ids, batch_texts, batch_metadatas = zip(*batch)

        start_time = time.time()
        embeddings = await asyncio.to_thread(
            vectorstore.embeddings.embed_documents, list(batch_texts)
        )
        end_time = time.time()
        print(
            f"Generated embeddings for batch {batch_idx + 1} in {end_time - start_time:.2f} seconds"
        )

        # Upsert to Chroma
        print(f"Upserting batch {batch_idx + 1} to Chroma")
        start_time = time.time()
        await asyncio.to_thread(
            vectorstore._collection.upsert,
            embeddings=embeddings,
            documents=list(batch_texts),
            metadatas=list(batch_metadatas),
            ids=list(batch_ids),
        )
        end_time = time.time()
        print(f"Upserted batch {batch_idx + 1} in {end_time - start_time:.2f} seconds")

    print(f"Saved {len(chunk_data)} chunks to Chroma for user {user_id}")
