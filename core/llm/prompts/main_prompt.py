from typing import Any, Dict, List
from core.constants import INTERNAL, EXTERNAL

def main_prompt(
    messages: list,
    chunks: str,
    question: str,
    summary: str,
    mode: str,
    web_search_results: List[Dict[str, Any]] = None,
    initial_search_answer: str = None,
    initial_search_results: List[Dict[str, Any]] = None,
):
    contents = []
    if mode == INTERNAL:
        contents.append(
            {
                "role": "system",
                "parts": (
                    "You are an expert assistant that answers questions based on the provided **documents**.\n"
                    "Your job is to give **clear, structured, and modular answers** using Markdown formatting.\n\n"
                    "###  Guidelines\n"
                    "- Use **headings (`##`, `###`)** for major sections.\n"
                    "- Use **bullet points** and **numbered lists** to organize ideas.\n"
                    "- Highlight important terms in **bold** and examples in *italics*.\n"
                    "- Avoid long paragraphs — keep each idea short and readable.\n"
                    "- Merge overlapping ideas and remove redundancy.\n"
                    "- If any information is missing, state:  *Information not found in available documents.*\n\n"
                    "###  Context Handling\n"
                    "- Extract and use as much relevant information as possible from the documents.\n"
                    "- If the question can be answered using the provided context, give a **direct, detailed, and specific answer**.\n"
                    "- If multiple sources contradict, mention it clearly using a note block.\n\n"
                    "###  Output Structure Example\n"
                    "```\n"
                    "## Overview\n"
                    "(Brief explanation)\n\n"
                    "## Key Details\n"
                    "- **Point 1:** Explanation...\n"
                    "- **Point 2:** Explanation...\n\n"
                    "## Additional Insights\n"
                    "- *Optional examples, comparisons, or clarifications.*\n\n"
                    "## Summary\n"
                    "(Final concise conclusion)\n"
                    "```\n"
                ),
            }
        )

        # Retrieved context
        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f" **Document Chunks (Context):**\n{chunks}\n",
                }
            )

        # Conversation history
        for m in messages:
            if m.type == "human":
                contents.append({"role": "user", "parts": m.content})
            elif m.type == "ai":
                contents.append({"role": "assistant", "parts": m.content})

        # Optional summary
        if summary:
            contents.append(
                {
                    "role": "system",
                    "parts": f" **Summary Reference:**\n{summary}\n",
                }
            )

    elif mode == EXTERNAL:
        contents.append(
            {
                "role": "system",
                "parts": (
                    "You are an expert assistant that answers questions using both **documents** and **external knowledge**.\n"
                    "Your task is to create **well-structured, modular Markdown answers** that are clear and easy to follow.\n\n"
                    " Guidelines\n"
                    "- Structure your answer with **sections, bullets, and bolded keywords**.\n"
                    "- Keep explanations concise and modular.\n"
                    "- Always **prioritize information from documents** over web results.\n"
                    "- If conflicting data exists, state clearly:  *Some sources provide conflicting information...*\n\n"
                    "###  Output Structure Example\n"
                    "```\n"
                    "## Overview\n"
                    "(Brief explanation)\n\n"
                    "## Key Information\n"
                    "- **Document Insight:** ...\n"
                    "- **Web Insight:** ...\n\n"
                    "## Conflicts or Gaps\n"
                    "-  *Some sources differ on...*\n\n"
                    "## Summary\n"
                    "(Concise conclusion)\n"
                    "```\n"
                ),
            }
        )

        # Retrieved context
        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f" **Document Chunks (Context):**\n{chunks}\n",
                }
            )

        # Initial external sources
        if initial_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f" **Initial External Knowledge Sources:**\n{initial_search_results}\n",
                }
            )

        # Conversation history
        for m in messages:
            if m.type == "human":
                contents.append({"role": "user", "parts": m.content})
            elif m.type == "ai":
                contents.append({"role": "assistant", "parts": m.content})

        # Summary context
        if summary:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Summary Reference:**\n{summary}\n",
                }
            )

        # Web search results
        if web_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"**Web Search Results:**\n{web_search_results}\n",
                }
            )

        # Initial web answer
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
                "parts": "If conflicting information exists, always **prioritize document content over web sources.**",
            }
        )

        # Final user question
    else:
        raise ValueError("Invalid mode. Mode must be either 'INTERNAL' or 'EXTERNAL'.")

    # Final user question
    contents.append({"role": "user", "parts": f" **Question:** {question}\n"})

    # JSON formatting requirement
    contents.append(
        {
            "role": "user",
            "parts": "Please return your response **only** in a valid JSON format containing the final synthesized Markdown answer.",
        }
    )

    return contents
