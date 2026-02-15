"""
Prompt builder for the streaming query path.

Reuses most of the logic from the main agent prompt but removes
structured-output / JSON constraints so the LLM can output clean
Markdown that is streamed token-by-token to the client.
"""

from typing import Any, Dict, List, Optional

from core.constants import EXTERNAL, INTERNAL


def build_streaming_prompt(
    *,
    messages: list,
    chunks: list,
    question: str,
    summary: Optional[str] = None,
    mode: str = INTERNAL,
    web_search_results: Optional[List[Dict[str, Any]]] = None,
    initial_search_answer: Optional[str] = None,
    initial_search_results: Optional[List[Dict[str, Any]]] = None,
    use_self_knowledge: bool = False,
    spreadsheet_schema: Optional[str] = None,
    sql_result: Optional[str] = None,
) -> str:
    """Build a single prompt string suitable for direct LLM streaming.

    Unlike :func:`main_prompt` this does **not** ask for JSON output or
    define structured actions.  The LLM is instructed to respond directly
    in Markdown.
    """

    parts: list[str] = []

    # ── System instructions ──────────────────────────────────────────
    if mode == INTERNAL:
        parts.append(
            "You are an expert assistant that answers questions based on "
            "the provided documents.\n"
            "Give clear, structured, and modular answers using Markdown.\n"
            "Use headings, bullet points, and bold text for readability.\n"
            "Rely strictly on the supplied data. If the data is insufficient, "
            "say so explicitly.\n"
        )
    elif mode == EXTERNAL:
        parts.append(
            "You are an expert assistant that answers questions using the "
            "provided documents and any supplied external data.\n"
            "Prioritise document content over web search results.\n"
            "Give clear, structured Markdown answers.\n"
            "If sources conflict, note the discrepancy.\n"
        )
    else:
        raise ValueError(f"Invalid mode: {mode}")

    # ── Document chunks ──────────────────────────────────────────────
    if chunks:
        parts.append(f"## Document Chunks (Context)\n{chunks}\n")

    # ── Summary ──────────────────────────────────────────────────────
    if summary:
        parts.append(f"## Summary Reference\n{summary}\n")

    # ── Spreadsheet schema ───────────────────────────────────────────
    if spreadsheet_schema:
        parts.append(
            "## Spreadsheet Data\n"
            f"```\n{spreadsheet_schema}\n```\n"
        )

    # ── SQL result ───────────────────────────────────────────────────
    if sql_result:
        parts.append(
            "## SQL Query Result\n"
            f"{sql_result}\n"
        )

    # ── Web search ───────────────────────────────────────────────────
    if initial_search_results:
        parts.append(
            f"## Initial External Sources\n{initial_search_results}\n"
        )
    if initial_search_answer:
        parts.append(
            f"## Initial Web Answer\n{initial_search_answer}\n"
        )
    if web_search_results:
        parts.append(f"## Web Search Results\n{web_search_results}\n")

    # ── Conversation history ─────────────────────────────────────────
    if messages:
        parts.append("## Conversation History")
        for m in messages:
            role = getattr(m, "type", "unknown")
            content = getattr(m, "content", str(m))
            if role == "human":
                parts.append(f"**User:** {content}")
            elif role == "ai":
                parts.append(f"**Assistant:** {content}")
        parts.append("")  # blank line

    # ── Question ─────────────────────────────────────────────────────
    parts.append(f"## Question\n{question}\n")
    parts.append(
        "Answer the question directly in well-structured Markdown. "
        "Do not wrap your answer in JSON or code blocks."
    )

    return "\n\n".join(parts)


def build_streaming_combination_prompt(
    query: str,
    sub_answers: list,
) -> str:
    """Prompt for streaming the combination of decomposed sub-answers."""
    import json

    sub_json = json.dumps(sub_answers, indent=2, ensure_ascii=False)
    return (
        "You are an expert assistant. Synthesise the following partial answers "
        "into one coherent, well-structured Markdown response.\n\n"
        f"**Question:** {query}\n\n"
        f"**Sub-answers:**\n{sub_json}\n\n"
        "Instructions:\n"
        "1. Combine all sub-answers into a single natural response.\n"
        "2. Remove redundancy but keep all distinct insights.\n"
        "3. Note contradictions clearly.\n"
        "4. Use headings, bullets, and bold text for readability.\n"
        "5. Return only the final Markdown answer.\n"
    )
