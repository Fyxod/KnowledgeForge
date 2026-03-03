"""Phase 2.1: CRAG Corrective Retrieval — Evaluator prompt."""

from typing import Any, Dict, List


def evaluator_prompt(query: str, chunks: List[Dict[str, Any]]) -> list:
    """
    Build the prompt for the CRAG retrieval evaluator.

    The evaluator assesses whether retrieved chunks are sufficient to answer
    the query and suggests re-retrieval if needed.
    """
    # Format chunks for the evaluator (show first 200 chars of each)
    chunk_summaries = []
    for i, chunk in enumerate(chunks[:10]):  # Evaluate max 10 chunks
        content = chunk.get("content", chunk.get("page_content", ""))[:200]
        title = chunk.get("title", chunk.get("metadata", {}).get("title", "Unknown"))
        score = chunk.get("rerank_score", chunk.get("relevance_score", 0.0))
        chunk_summaries.append(
            f"Chunk {i + 1} (score: {score:.2f}, doc: {title}):\n{content}..."
        )

    chunks_text = "\n\n".join(chunk_summaries) if chunk_summaries else "No chunks retrieved."

    contents = [
        {
            "role": "system",
            "parts": (
                "You are a retrieval quality evaluator. Your job is to assess whether "
                "the retrieved document chunks contain sufficient information to answer "
                "the user's query.\n\n"
                "Evaluate based on:\n"
                "1. **Relevance**: Do the chunks actually discuss the topic of the query?\n"
                "2. **Completeness**: Do the chunks contain enough detail to form a meaningful answer?\n"
                "3. **Coverage**: For multi-part questions, are all parts addressed?\n\n"
                "Choose one verdict:\n"
                "- **sufficient**: The chunks contain relevant information to answer the query. "
                "Even partial information counts as sufficient if it addresses the core question.\n"
                "- **ambiguous**: The chunks are tangentially related but don't directly answer "
                "the query. A refined query might find better results.\n"
                "- **insufficient**: The chunks are completely irrelevant to the query.\n\n"
                "If verdict is 'ambiguous' or 'insufficient', you MUST provide a refined_query "
                "that rephrases the question using different terms, synonyms, or a more specific "
                "angle. Use synonyms and alternative terminology that might appear in the documents "
                "(e.g., 'deliverables' ↔ 'objectives', 'goals' ↔ 'targets', 'revenue' ↔ 'income'). "
                "The refined query should help retrieve chunks that the original query missed.\n\n"
                "Be lenient — if there is ANY useful information, choose 'sufficient'. "
                "Only choose 'ambiguous' or 'insufficient' when chunks truly miss the mark."
            ),
        },
        {
            "role": "user",
            "parts": (
                f"**User Query:** {query}\n\n"
                f"**Retrieved Chunks:**\n{chunks_text}\n\n"
                "Evaluate these chunks and return your verdict as JSON."
            ),
        },
    ]
    return contents
