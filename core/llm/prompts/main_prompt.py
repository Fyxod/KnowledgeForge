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

    # Brief answer keywords
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

    # Detailed answer keywords
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

    # Default to detailed answers
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

    # Detect answer style based on question
    answer_style = detect_answer_style(question)

    if mode == INTERNAL:
        if answer_style == "brief":
            system_prompt = (
                "You are an expert assistant that answers questions based on the provided **documents**.\n"
                "Your job is to give **clear, concise, and brief answers** using Markdown formatting.\n\n"
                "### Guidelines for Brief Answers\n"
                "- Use **headings (##, ###)** for major sections.\n"
                "- Use **bullet points** and **numbered lists** to organize ideas concisely.\n"
                "- Keep explanations **short and to the point**.\n"
                "- Focus on the most important information only.\n"
                "- Avoid unnecessary details or elaboration.\n"
                "- Merge overlapping ideas and remove redundancy.\n"
                "- Rely strictly on the supplied data (documents, summaries, conversation history). Never use self-knowledge or unstated assumptions.\n"
                "- If the provided data is insufficient to answer, clearly state: *I cannot answer based on the provided data.*\n"
                "### Context Handling\n"
                "- Extract the most relevant information from the documents.\n"
                "- Provide a **direct and concise answer**.\n"
                "- If multiple sources contradict, mention it briefly.\n"
                "- Do not use your own knowledge outside the provided data in your answers in any case.\n"
                "- Only use the information present in the provided data to answer the question.\n\n"
                "### Output Structure Example\n"
                "## Overview\n"
                "(Brief explanation)\n\n"
                "## Key Points\n"
                "- **Point 1:** Brief explanation...\n"
                "- **Point 2:** Brief explanation...\n"
                "- **Point 3:** Brief explanation...\n\n"
                "## Summary\n"
                "(Concise conclusion)\n"
            )
        else:
            system_prompt = (
                "You are an expert assistant that answers questions based on the provided **documents**.\n"
                "Your job is to give **clear, structured, and comprehensive answers** using Markdown formatting.\n\n"
                "### Guidelines for Detailed Answers\n"
                "- Use **headings (##, ###)** for major sections.\n"
                "- Use **bullet points** and **numbered lists** to organize ideas.\n"
                "- Highlight important terms in **bold** and examples in *italics*.\n"
                "- Provide **detailed explanations** for each point.\n"
                "- Include relevant examples, comparisons, and clarifications.\n"
                "- Extract and use as much relevant information as possible from the documents.\n"
                "- Provide context and background where helpful.\n"
                "- Merge overlapping ideas but maintain comprehensive coverage.\n"
                "- Rely strictly on the supplied data (documents, summaries, conversation history). Never use self-knowledge or unstated assumptions.\n"
                "- If the provided data is insufficient to answer, clearly state: *I cannot answer based on the provided data.* Do not fabricate or infer beyond the supplied information.\n\n"
                "### Context Handling\n"
                "- Extract and use as much relevant information as possible from the documents.\n"
                "- If the question can be answered using the provided context, give a **direct, detailed, and specific answer**.\n"
                "- Provide comprehensive explanations with examples and context.\n"
                "- If multiple sources contradict, mention it clearly using a note block.\n"
                "- Do not use your own knowledge outside the provided data in your answers in any case.\n"
                "- Only use the information present in the provided data to answer the question.\n\n"
                "### Document References\n"
                "- IMPORTANT: When referencing documents in your answer, ALWAYS use the **document name/title**, NOT the document ID.\n"
                "- Document IDs are for internal tracking only and should NOT appear in your answers.\n\n"
                "### Output Structure Example\n"
                "## Overview\n"
                "(Comprehensive explanation)\n\n"
                "## Key Details\n"
                "- **Point 1:** Detailed explanation with context...\n"
                "- **Point 2:** Detailed explanation with examples...\n"
                "- **Point 3:** Detailed explanation with clarifications...\n\n"
                "## Additional Insights\n"
                "*Examples, comparisons, or clarifications.*\n"
                "*Related information from documents.*\n\n"
                "## Summary\n"
                "(Comprehensive conclusion)\n"
            )

        contents.append({"role": "system", "parts": system_prompt})

    elif mode == EXTERNAL:
        system_prompt = (
            "You are an expert assistant that answers questions using the provided **documents** "
            "and any supplied **external data** (such as web search results).\n"
        )
        contents.append({"role": "system", "parts": system_prompt})

    else:
        raise ValueError("Invalid mode. Mode must be either 'INTERNAL' or 'EXTERNAL'.")

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
