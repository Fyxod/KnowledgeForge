import os
import time
from typing import Optional, Dict, Any

from langchain_chroma import Chroma
from core.embeddings.embeddings import get_embedding_function

# We reuse the same embedding function to ensure distances match RAG
embedding_function = get_embedding_function()

# A very tight distance threshold: only near-exact matches will hit the cache.
# Range is typical for cosine distance from nomic-embed-text (0.0=identical)
DEFAULT_CACHE_THRESHOLD = 0.10

class SemanticCacheManager:
    """
    Manages a local Semantic Cache using ChromaDB to store and rapidly retrieve 
    answers for identical or highly similar user queries, saving GPU computing time.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        # Use a separate persist directory specifically for the cache
        self.persist_path = os.path.join("data", user_id, "semantic_cache")
        os.makedirs(self.persist_path, exist_ok=True)
        
        self.vectorstore = Chroma(
            collection_name="query_cache",
            persist_directory=self.persist_path,
            embedding_function=embedding_function,
        )

    def check_cache(self, query: str, threshold: float = DEFAULT_CACHE_THRESHOLD) -> Optional[Dict[str, Any]]:
        """
        Check if an answer for this query already exists in the cache.
        Returns the cached payload if a match within the threshold is found, otherwise None.
        """
        try:
            # We use similarity_search_with_score to evaluate the distance
            # For Chroma and Langchain (cosine/L2), lower score = closer distance
            results = self.vectorstore.similarity_search_with_score(query, k=1)
            
            if not results:
                print(f"[CACHE] No cached results found for user {self.user_id}")
                return None
            
            best_match, score = results[0]
            
            print(f"[CACHE] Best match score: {score:.4f} against threshold {threshold}")
            if score <= threshold:
                print(f"[CACHE HIT] Found match for query: '{query}'")
                
                # Reconstruct the response from the cached metadata
                cached_data = {
                    "answer": best_match.metadata.get("answer"),
                    "confidence_score": best_match.metadata.get("confidence_score", "high"),
                    "timestamp": best_match.metadata.get("timestamp"),
                    "cached": True
                }
                
                # Attempt to parse jsonified sources if they were stored
                sources_str = best_match.metadata.get("sources", "{}")
                import json
                try:
                    cached_data["sources"] = json.loads(sources_str)
                except json.JSONDecodeError:
                    cached_data["sources"] = {"documents_used": [], "web_used": []}
                    
                return cached_data
            
            print(f"[CACHE MISS] Semantic distance {score:.4f} > {threshold}")
            return None
            
        except Exception as e:
            print(f"[CACHE] Error checking semantic cache: {str(e)}")
            return None

    def add_to_cache(self, query: str, answer: str, sources: Dict[str, Any], confidence_score: str):
        """
        Embeds a new query and saves its final answer and sources to the cache.
        """
        try:
            # Generate a unique ID for this cache entry based on current time
            cache_id = f"cache_{int(time.time()*1000)}"
            
            import json
            metadata = {
                "answer": answer,
                "confidence_score": confidence_score,
                "timestamp": time.time(),
                # Store sources as a serialized JSON string to bypass metadata type restrictions
                "sources": json.dumps(sources)
            }
            
            self.vectorstore.add_texts(
                texts=[query],
                metadatas=[metadata],
                ids=[cache_id]
            )
            print(f"[CACHE PUT] Successfully cached query: '{query}'")
            
        except Exception as e:
            print(f"[CACHE] Error adding to semantic cache: {str(e)}")

    def clear_cache(self):
        """
        Deletes all cached queries for the user.
        """
        try:
            # Delete the collection, which removes all vectors
            self.vectorstore.delete_collection()
            # Recreate an empty collection
            self.vectorstore = Chroma(
                collection_name="query_cache",
                persist_directory=self.persist_path,
                embedding_function=embedding_function,
            )
            print(f"[CACHE] Cleared cache for user {self.user_id}")
        except Exception as e:
            print(f"[CACHE] Error clearing cache: {str(e)}")
