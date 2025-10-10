from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def summarize_documents_prompt(document: str):
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert assistant specialized in **structured document summarization**.\n"
                "Your goal is to create a **clear, modular, Markdown-formatted summary** of the given document.\n\n"
                "### Formatting & Style Guidelines\n"
                "- Use **headings (`##`, `###`)** for logical sections.\n"
                "- Use **bullet points** to list facts or details.\n"
                "- Highlight key terms in **bold** and examples in *italics*.\n"
                "- Avoid long paragraphs; keep content concise and easy to read.\n\n"
                "###  Structure Example\n"
                "```\n"
                "# [Concise 3-7 word Title]\n\n"
                "## Overview\n"
                "(Brief overview of document purpose or theme)\n\n"
                "## Key Sections or Themes\n"
                "- **Section 1:** Main ideas or findings\n"
                "- **Section 2:** Supporting details or analysis\n\n"
                "## Important Details\n"
                "- **Fact 1:** ...\n"
                "- **Fact 2:** ...\n\n"
                "## Summary\n"
                "(Concise recap or implications)\n"
                "```\n\n"
                "### Output Requirements\n"
                "- Summary length: **300-1000 words**\n"
                "- Do **not** omit significant details.\n"
                "- Escape any quotes, newlines, or special characters that could break JSON formatting.\n"
            ),
        },
        {
            "role": "user",
            "parts": f" **Document to Summarize:**\n\n{document}\n\nPlease summarize in 300-1000 words following the structure above.",
        },
    ]
    return contents



def global_summarization_prompt(summaries: str):
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert assistant that **synthesizes multiple summaries** into one coherent, modular, and structured Markdown summary.\n\n"
                "### Objectives\n"
                "- Capture recurring **themes**, **key points**, and **insights** across summaries.\n"
                "- Group similar ideas together logically.\n"
                "- Avoid personal interpretation — focus on **common findings**.\n"
                "- Ensure readability using Markdown structure.\n\n"
                "###  Recommended Structure\n"
                "```\n"
                "# [Concise Combined Title]\n\n"
                "## Common Themes\n"
                "- **Theme 1:** Explanation...\n"
                "- **Theme 2:** Explanation...\n\n"
                "## Shared Insights\n"
                "- **Insight 1:** ...\n"
                "- **Insight 2:** ...\n\n"
                "## Notable Variations\n"
                "- *Some sources differ on...*\n\n"
                "## Overall Summary\n"
                "(Unified conclusion)\n"
                "```\n\n"
                "###  Output Requirements\n"
                "- Summary length: **500-1000 words**\n"
                "- Output **only** a valid JSON object containing the Markdown summary.\n"
                "- Escape quotes, newlines, or special characters.\n"
                "- Do **not** add commentary outside the JSON.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f" **Summaries to Combine:**\n{summaries}\n\n"
                "Generate a single, coherent, Markdown-formatted summary (500-1000 words) that merges recurring and essential ideas.\n\n"
                "Return a valid JSON object containing your final synthesized summary."
            ),
        },
    ]
    return contents

multi_document_summarization_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are an expert assistant for **multi-document summarization**.\n"
                "Each document should be summarized **independently** in a modular Markdown format.\n\n"
                "###  Summary Guidelines\n"
                "- Capture **key ideas, themes, and essential points** from each document.\n"
                "- Use **Markdown structure** with headings and bullets.\n"
                "- Avoid copying large text blocks; rephrase while preserving meaning.\n"
                "- If a document has multiple topics, reflect that clearly with subheadings.\n"
                "- Keep each summary **concise and factual**, between 200-800 words.\n"
            )
        ),
        SystemMessage(
            content=(
                "###  Output Requirements\n"
                "- Escape any quotes, newlines, or special characters inside strings.\n"
                "- Return output **as a list of JSON objects**, where each object includes:\n"
                "  - `document_id`: (unique identifier)\n"
                "  - `summary`: (Markdown-formatted structured summary)\n"
            )
        ),
        SystemMessage(
            content=(
                "Your goal is to generate **high-quality, structured summaries** suitable for semantic search, retrieval, or further AI processing."
            )
        ),
        HumanMessagePromptTemplate.from_template(
            " **Documents to Summarize:**\n\n{documents}\n\n"
            "Please return a **JSON list** where each item has this structure:\n"
            "- `document_id`: unique identifier of the document\n"
            "- `summary`: Markdown-formatted summary with sections and bullet points"
        ),
    ]
)
