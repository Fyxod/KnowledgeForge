from typing import Any, Dict, List

from core.constants import EXTERNAL, INTERNAL


def detect_answer_style(question: str) -> str:
    """
    Detect the desired answer style based on keywords in the question.

    Returns:
       'brief'    - User wants a concise answer
       'detailed' - User wants a detailed answer
       'normal'   - Default to detailed answers
    """
    question_lower = question.lower()

    brief_keywords = [
        "3 bullet points",
        "summarize",
        "brief",
        "short",
        "concise",
        "in short",
        "quick summary",
    ]
    for keyword in brief_keywords:
        if keyword in question_lower:
            return "brief"

    detailed_keywords = [
        "detailed",
        "elaborate",
        "explain in detail",
        "comprehensive",
        "in depth",
        "thorough",
    ]
    for keyword in detailed_keywords:
        if keyword in question_lower:
            return "detailed"

    return "detailed"


def main_prompt(
    messages: list,
    chunks: str,
    question: str,
    summary: str,
    mode: str,
    web_search_results: List[Dict[str, Any]] = None,
    initial_search_answer: str = None,
    initial_search_results: List[Dict[str, Any]] = None,
    use_self_knowledge: bool = False,
):
    contents = []

    answer_style = detect_answer_style(question)

    # =========================
    # INTERNAL MODE
    # =========================
    if mode == INTERNAL:
        if answer_style == "brief":
            system_prompt = (
                "You are an expert assistant that answers questions based on the provided **documents**.\n"
                "Your job is to give **clear, concise, and brief answers** using Markdown formatting.\n\n"
                "### Guidelines for Brief Answers\n"
                "- Use headings (##, ###).\n"
                "- Use bullets and numbered lists.\n"
                "- Keep explanations short.\n"
                "- Focus only on key information.\n"
                "- Avoid unnecessary elaboration.\n"
                "- Never use self-knowledge.\n"
                "- If insufficient data, state clearly you cannot answer.\n\n"
                "### Output Structure\n"
                "## Overview\n"
                "## Key Points\n"
                "## Summary\n"
            )
        else:
            system_prompt = (
                "You are an expert assistant that answers questions based on the provided **documents**.\n"
                "Your job is to give **clear, structured, and comprehensive answers** using Markdown formatting.\n\n"
                "### Guidelines for Detailed Answers\n"
                "- Use headings (##, ###).\n"
                "- Use structured bullets and lists.\n"
                "- Highlight important terms in bold.\n"
                "- Provide detailed explanations.\n"
                "- Include examples and clarifications.\n"
                "- Extract maximum relevant information from documents.\n"
                "- Never use self-knowledge.\n"
                "- If insufficient data, clearly state inability to answer.\n\n"
                "### Document References\n"
                "- Always use document name/title, not document ID.\n\n"
                "### Output Structure\n"
                "## Overview\n"
                "## Key Details\n"
                "## Additional Insights\n"
                "## Summary\n"
            )

        contents.append({"role": "system", "parts": system_prompt})

        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Document Chunks (Context):**\n{chunks}\n",
                }
            )

    # =========================
    # EXTERNAL MODE
    # =========================
    elif mode == EXTERNAL:
        if answer_style == "brief":
            system_prompt = (
                "You are an expert assistant that answers questions using provided **documents** "
                "and supplied **external data** (e.g., web search results).\n\n"
                "- Keep answers concise and structured.\n"
                "- Prioritize document data over web data.\n"
                "- If conflict exists, mention briefly.\n"
                "- If insufficient data, explicitly state inability to answer.\n"
            )
        else:
            system_prompt = (
                "You are an expert assistant that answers questions using provided **documents** "
                "and supplied **external data** (e.g., web search results).\n\n"
                "- Provide comprehensive structured answers.\n"
                "- Prioritize document data over web data.\n"
                "- Mention conflicting information clearly.\n"
                "- If insufficient data, explicitly state inability to answer.\n"
                "- Use document name/title when referencing.\n"
            )

        contents.append({"role": "system", "parts": system_prompt})

        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Document Chunks (Context):**\n{chunks}\n",
                }
            )

        if initial_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Initial External Knowledge Sources:**\n{initial_search_results}\n",
                }
            )

        if web_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Web Search Results:**\n{web_search_results}\n",
                }
            )

        if initial_search_answer:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Initial Web Search Answer:**\n{initial_search_answer}\n",
                }
            )

        contents.append(
            {
                "role": "system",
                "parts": (
                    "If conflicting information exists, always prioritize document content over web sources.\n"
                    "If no provided data resolves the question, respond that you cannot answer based on the provided data."
                ),
            }
        )

    else:
        raise ValueError("Invalid mode. Mode must be either 'INTERNAL' or 'EXTERNAL'.")

    # =========================
    # Conversation History
    # =========================
    for m in messages:
        if m.type == "human":
            contents.append({"role": "user", "parts": m.content})
        elif m.type == "ai":
            contents.append({"role": "assistant", "parts": m.content})

    # =========================
    # Summary Context
    # =========================
    if summary:
        contents.append(
            {"role": "system", "parts": f"**Summary Reference:**\n{summary}\n"}
        )

    # =========================
    # Title Warning
    # =========================
    contents.append(
        {
            "role": "system",
            "parts": "Don't give too much importance to the title while giving answer as titles may be vague filenames.",
        }
    )

    # =========================
    # Action Definitions
    # =========================
    action_block = (
        "You can perform the following actions:\n"
        "- **answer**: Directly answer using available information.\n"
    )

    if mode == EXTERNAL:
        action_block += "- **web_search**: Search for recent or external information.\n"

    action_block += (
        "- **document_summarizer**: Request summary of a specific document.\n"
        "- **global_summarizer**: Request collective summary of all documents.\n"
        "- **failure**: Indicate inability to answer.\n"
        "Do not choose actions lightly.\n"
    )

    contents.append({"role": "system", "parts": action_block})

    # =========================
    # Final Question
    # =========================
    contents.append(
        {
            "role": "user",
            "parts": "Please use all the provided information to answer the question.",
        }
    )

    contents.append({"role": "user", "parts": f"**Question:** {question}\n"})

    contents.append(
        {
            "role": "user",
            "parts": "Please return your response **only** in a valid JSON format containing the final synthesized Markdown answer.",
        }
    )

    return contents
