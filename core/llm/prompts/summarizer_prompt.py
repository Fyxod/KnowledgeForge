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
                "- Don't just provide a paragraph summary; break down the content into sections with headings and bullet points.\n\n"
                "###  Structure Example\n"
                "```\n"
                "# [Mandatory Concise 3-7 word Title]\n\n"
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
                "- Please provide the summary in **valid parsable Markdown format only**.\n"
            ),
        },
        {
            "role": "user",
            "parts": f" **Document to Summarize:**\n\n{document}\n\nPlease summarize in 300-1000 words following the structure above.",
        },
    ]
    return contents


def combine_summaries_prompt(title: str, partial_summaries: list[str]):
    contents = [
        {
            "role": "system",
            "parts": (
                "You are an expert assistant that merges section-level summaries into one cohesive, structured Markdown summary.\n\n"
                "### Formatting & Structure\n"
                "- Begin with a mandatory level-1 heading (`#`) featuring a concise, neutral title.\n"
                "- Organize content with logical level-2/3 headings and bullet points.\n"
                "- Highlight key concepts with **bold** text and optional *italicized* examples.\n"
                "- Keep paragraphs short, factual, and neutral in tone.\n"
                "### Output Requirements\n"
                "- Preserve all key ideas while eliminating redundancy.\n"
                "- Maintain logical flow across sections.\n"
                "- Return only the structured Markdown summary (no additional commentary).\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f"**Document Title:** {title}\n\n"
                f"**Section Summaries:** {partial_summaries}\n\n"
                "Please synthesize these into one cohesive, Markdown-formatted summary that follows the structure guidelines above.\n"
                "Please provide the summary in **valid parsable Markdown format only**.\n"
            ),
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
                "- Ensure readability using Markdown structure with headings and bullet points.\n\n"
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
                "- Summary length: **500-1000 words**.\n"
                "- Use clear headings (`#`, `##`, `###`) and bullet points throughout.\n"
                "- Highlight critical concepts in **bold** and optional examples in *italics*.\n"
                "- Please provide the summary in **valid parsable Markdown format only**.\n"
            ),
        },
        {
            "role": "user",
            "parts": (
                f" **Summaries to Combine:**\n{summaries}\n\n"
                "Generate a single, coherent, Markdown-formatted summary (500-1000 words) that merges recurring and essential ideas.\n\n"
                "Return a valid JSON object containing your final Markdown summary."
            ),
        },
    ]
    return contents
