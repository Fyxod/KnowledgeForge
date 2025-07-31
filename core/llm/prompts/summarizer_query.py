from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

summarize_documents_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant tasked with summarizing documents for efficient understanding and retrieval. "
                "Your job is to read the provided document or text and produce a clear, concise summary that captures the main ideas without losing critical details."
            )
        ),
        SystemMessage(
            content=(
                "If the document contains multiple sections or themes, organize the summary accordingly. "
                "Be objective and do not add your own interpretations or information not present in the original content. "
                "Focus on clarity, coherence, and informativeness."
            )
        ),
        SystemMessage(
            content=(
                "The goal is to provide a useful and accurate summary that reflects the content and intent of the original document, suitable for downstream tasks like search or knowledge retrieval."
            )
        ),
        HumanMessagePromptTemplate.from_template(
            "Document to summarize:\n\n{document}\n\nSummary:"
        ),
    ]
)

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

global_summarization_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant tasked with synthesizing multiple summaries into one cohesive and insightful summary. "
                "Your goal is to capture the most important and recurring themes, key points, and insights that appear across all the provided summaries."
            )
        ),
        SystemMessage(
            content=(
                "Ensure the synthesized summary is clear, concise, and representative of the collective content. "
                "Try to capture all major themes and insights without introducing new information or interpretations."
                "Group similar ideas, highlight common findings, and present overarching insights without adding your own interpretation."
            )
        ),
        SystemMessage(
            content=(
                "The final output should serve as a high-level overview of the set of documents, suitable for understanding shared themes or guiding further exploration."
            )
        ),
        HumanMessagePromptTemplate.from_template(
            "You will be provided with a list of document summaries. Generate a single, coherent summary that captures the recurring and most important ideas across them.\n\n"
            "Summaries:\n{summaries}\n\n"
            "Return:\n"
            "- `Summary`: a comprehensive, concise summary of the insights, themes, and key points across all provided summaries."
        ),
    ]
)

