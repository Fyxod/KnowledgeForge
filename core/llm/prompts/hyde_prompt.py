"""Phase 2.3: HyDE — Hypothetical Document Embeddings prompt."""


def hyde_prompt(query: str) -> list:
    """
    Build the prompt for generating a hypothetical document passage.

    HyDE works by generating a hypothetical answer/passage that would appear
    in a document that answers the query. This passage is then embedded and
    used for vector search, bridging the query-document language gap.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are a technical document passage generator. Given a question, "
                "write a short passage (50-150 words) that would appear in a document "
                "that answers this question. Write it as a factual excerpt — not as an "
                "answer to the question, but as a passage from a source document.\n\n"
                "Guidelines:\n"
                "- Use domain-specific terminology relevant to the question\n"
                "- Write in a formal, document-like tone\n"
                "- Include specific details, names, and terms that a real document would contain\n"
                "- Do NOT write 'This document...' or reference the question directly\n"
                "- Just write the passage content as if copied from a real document"
            ),
        },
        {
            "role": "user",
            "parts": f"Generate a hypothetical document passage for this query:\n\n{query}",
        },
    ]
    return contents
