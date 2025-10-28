from typing import Any, Dict, List
from core.constants import INTERNAL, EXTERNAL


def self_knowledge_prompt(
    messages: list,
    question: str,
):
    contents = []
    contents.append(
        {
            "role": "system",
            "parts": (
                "You are an expert assistant that answers questions based on your own knowledge.\n"
                "Your job is to give **clear, structured, and modular answers** using Markdown formatting.\n\n"
                "###  Guidelines\n"
                "- Use **headings (`##`, `###`)** for major sections.\n"
                "- Use **bullet points** and **numbered lists** to organize ideas.\n"
                "- Highlight important terms in **bold** and examples in *italics*.\n"
                "- Avoid long paragraphs — keep each idea short and readable.\n"
                "- Merge overlapping ideas and remove redundancy.\n\n"
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
