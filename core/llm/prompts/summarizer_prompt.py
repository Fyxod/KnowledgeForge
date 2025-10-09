from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def summarize_documents_prompt(document: str):

    contents = [
        {
            "role": "user",
            "parts": f"Document to summarize:\n\n{document} Please summarize in 300-1000 words:",
        },
        {
            "role": "system",
            "parts": (
                "You are a helpful assistant tasked with summarizing documents. "
                "Write a comprehensive summary between 300-1000 words. "
                "The summary should not exceed 1000 words. "
                "Do not skip over important details, even if they seem minor. "
                "If the document contains multiple sections or themes, organize the summary accordingly. "
                "Use multiple paragraphs and preserve important details. "
                "Also give a 3-7 words concise title for the summary."
                "Escape any quotes, newlines, or special characters inside strings that might affect json formatting.\n"
            ),
        },
    ]

    return contents


def global_summarization_prompt(summaries: str):
    contents = [
        {
            "role": "system",
            "parts": (
                "You are a helpful assistant tasked with synthesizing multiple summaries into one cohesive and insightful summary. "
                "Your goal is to capture the most important and recurring themes, key points, and insights that appear across all the provided summaries."
            ),
        },
        {
            "role": "system",
            "parts": (
                "Ensure the synthesized summary is clear, concise, and representative of the collective content. "
                "Group similar ideas, highlight common findings, and present overarching insights without adding your own interpretation."
            ),
        },
        {
            "role": "system",
            "parts": (
                "IMPORTANT INSTRUCTIONS FOR OUTPUT:\n"
                "- Return output **only as a valid JSON object** matching the schema.\n"
                "- Escape any quotes, newlines, or special characters inside strings.\n"
                "- Do not add commentary or text outside the JSON.\n"
                "- Make sure the JSON is complete and closed properly with curly braces."
            ),
        },
        {
            "role": "user",
            "parts": (
                "You will be provided with a list of document summaries. Generate a single, coherent summary that captures the recurring and most important ideas across them.\n\n"
                "Return proper JSON. "
                "Escape any quotes, newlines, or special characters inside strings that might affect json formatting.\n"
                f"Summaries:\n{summaries}\n\n"
                "Summary (500 - 1000 words):"
            ),
        },
    ]

    return contents


multi_document_summarization_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant tasked with summarizing multiple documents for efficient understanding and downstream use. "
                "Each document you receive should be summarized independently. Your summary should capture the key ideas, themes, and essential information from the document, without adding your own interpretation."
            )
        ),
        SystemMessage(
            content=(
                "Ensure summaries are clear, concise, and accurate. "
                "Escape any quotes, newlines, or special characters inside strings.\n"
                "If a document contains multiple sections or topics, reflect that in the summary. "
                "Do not copy large blocks of text; rephrase in your own words while preserving the original meaning."
            )
        ),
        SystemMessage(
            content=(
                "The goal is to generate structured, high-quality summaries for each input document, suitable for semantic search, retrieval, or analysis."
            )
        ),
        HumanMessagePromptTemplate.from_template(
            "You will be provided with a list of documents. For each document, return a summary following the structure below.\n\n"
            "Documents:\n{documents}\n\n"
            "Return a list of objects where each object contains:\n"
            "- `document_id`: a unique identifier for the document (provided in input)\n"
            "- `summary`: a concise and complete summary of the document's content"
        ),
    ]
)
