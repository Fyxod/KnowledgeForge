from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

# summarize_documents_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant tasked with summarizing documents for efficient understanding and retrieval. "
#                 "Your job is to read the provided document or text and produce a clear, concise summary of 600 - 800 words that captures the main ideas without losing critical details."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "If the document contains multiple sections or themes, organize the summary accordingly. "
#                 "Be objective and do not add your own interpretations or information not present in the original content. "
#                 "Focus on clarity, coherence, and informativeness."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "The goal is to provide a useful and accurate summary that reflects the content and intent of the original document, suitable for downstream tasks like search or knowledge retrieval."
#             )
#         ),
#         HumanMessagePromptTemplate.from_template(
#             "Document to summarize:\n\n{document}\n\nSummary:"
#         ),
#     ]
# )
# summarize_documents_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "Write a summary of the document that is between 500-700 words.\n"
#                 "- Structure it in multiple paragraphs.\n"
#                 "- Expand on key events, characters, and themes.\n"
#                 "- Do not skip over important details, even if they seem minor.\n"
#                 "- Avoid single-paragraph answers."
#                 # "If your output is shorter than 500 words, continue writing until you reach the target length."
#             )
#         ),
#         HumanMessagePromptTemplate.from_template(
#             "Document to summarize:\n\n{document}\n\nSummary:"
#         ),
#     ]
# )

def summarize_documents_prompt(document: str):

    contents = [
        # {
        #     "role": "system",
        #     "parts": (
        #         "You are a helpful assistant tasked with summarizing documents. "
        #         "Write a comprehensive summary between 300-1000 words. "
        #         "The summary should not exceed 1000 words. "
        #         "Do not skip over important details, even if they seem minor. "
        #         "If the document contains multiple sections or themes, organize the summary accordingly. "
        #         "Use multiple paragraphs and preserve important details. "
        #         "Also give a 3-7 words concise title for the summary."
        #         "Escape any quotes, newlines, or special characters inside strings that might affect json formatting.\n"
        #     )
        # },
        {
            "role": "user",
            "parts": f"Document to summarize:\n\n{document} Please summarize in 300-1000 words:"
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
            )
        },
    ]

    return contents

# summarize_documents_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant tasked with summarizing documents. "
#                 "Write a comprehensive summary between 500-700 words. "
#                 "The summary should not exceed 700 words."
#                 "Do not skip over important details, even if they seem minor. "
#                 "If the document contains multiple sections or themes, organize the summary accordingly. "
#                 "Use multiple paragraphs and preserve important details."
#                 "Escape any quotes, newlines, or special characters inside strings that might affect json formatting.\n"
#             )
#         ),
#         HumanMessagePromptTemplate.from_template(
#             "Document to summarize:\n\n{document}\n\nSummary (500-700 words):"
#         ),
#     ]
# )

def global_summarization_prompt(summaries: str):
    contents = [
        {
            "role": "system",
            "parts": (
                "You are a helpful assistant tasked with synthesizing multiple summaries into one cohesive and insightful summary. "
                "Your goal is to capture the most important and recurring themes, key points, and insights that appear across all the provided summaries."
            )
        },
        {
            "role": "system",
            "parts": (
                "Ensure the synthesized summary is clear, concise, and representative of the collective content. "
                "Group similar ideas, highlight common findings, and present overarching insights without adding your own interpretation."
            )
        },
        {
            "role": "system",
            "parts": (
                "IMPORTANT INSTRUCTIONS FOR OUTPUT:\n"
                "- Return output **only as a valid JSON object** matching the schema.\n"
                "- Escape any quotes, newlines, or special characters inside strings.\n"
                "- Do not add commentary or text outside the JSON.\n"
                "- Make sure the JSON is complete and closed properly with curly braces."
            )
        },
        {
            "role": "user",
            "parts": (
                "You will be provided with a list of document summaries. Generate a single, coherent summary that captures the recurring and most important ideas across them.\n\n"
                "Return proper JSON. "
                "Escape any quotes, newlines, or special characters inside strings that might affect json formatting.\n"
                f"Summaries:\n{summaries}\n\n"
                "Summary (500 - 1000 words):"
            )
        }
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

# global_summarization_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant tasked with synthesizing multiple summaries into one cohesive and insightful summary. "
#                 "Your goal is to capture the most important and recurring themes, key points, and insights that appear across all the provided summaries."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "Ensure the synthesized summary is clear, concise, and representative of the collective content. "
#                 "Group similar ideas, highlight common findings, and present overarching insights without adding your own interpretation."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "IMPORTANT INSTRUCTIONS FOR OUTPUT:\n"
#                 "- Return output **only as a valid JSON object** matching the schema.\n"
#                 "- Escape any quotes, newlines, or special characters inside strings.\n"
#                 "- Do not add commentary or text outside the JSON.\n"
#                 "- Make sure the JSON is complete and closed properly with curly braces."
#             )
#         ),
#         HumanMessagePromptTemplate.from_template(
#             "You will be provided with a list of document summaries. Generate a single, coherent summary that captures the recurring and most important ideas across them.\n\n"
#             "Return proper JSON "
#             "Escape any quotes, newlines, or special characters inside strings that might affect json formatting.\n"
#             "Summaries:\n{summaries}\n\n"
#             "Summary(500 - 1000 words):"
#         ),
#     ]
# )


# global_summarization_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant tasked with synthesizing multiple summaries into one cohesive and insightful summary. "
#                 "Your goal is to capture the most important and recurring themes, key points, and insights that appear across all the provided summaries."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "Ensure the synthesized summary is clear, concise, and representative of the collective content. "
#                 "Try to capture all major themes and insights without introducing new information or interpretations."
#                 "Group similar ideas, highlight common findings, and present overarching insights without adding your own interpretation."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "The final output should serve as a high-level overview of the set of documents, suitable for understanding shared themes or guiding further exploration."
#             )
#         ),
#         HumanMessagePromptTemplate.from_template(
#             "You will be provided with a list of document summaries. Generate a single, coherent summary that captures the recurring and most important ideas across them.\n\n"
#             "Summaries:\n{summaries}\n\n"
#             "Return:\n"
#             "- `Summary`: a comprehensive, concise summary of the insights, themes, and key points across all provided summaries."
#         ),
#     ]
# )
# global_summarization_prompt = ChatPromptTemplate.from_messages(
#     [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant tasked with synthesizing multiple summaries into one cohesive and insightful summary. "
#                 "Your goal is to capture the most important and recurring themes, key points, and insights that appear across all the provided summaries."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "Ensure the synthesized summary is clear, structured, and representative of the collective content. "
#                 "Group similar ideas, highlight common findings, and present overarching insights without introducing new information or interpretations."
#             )
#         ),
#         SystemMessage(
#             content=(
#                 "The final output should serve as a high-level overview of the set of documents, suitable for understanding shared themes or guiding further exploration. "
#                 "The summary must be between 700 and 1000 words."
#             )
#         ),
#         HumanMessagePromptTemplate.from_template(
#             "You will be provided with a list of document summaries. Generate a single, coherent summary that captures the recurring and most important ideas across them.\n\n"
#             "Summaries:\n{summaries}\n\n"
#             "Return:\n"
#             "- `Summary`: a comprehensive, well-structured synthesis (700–1000 words) of the insights, themes, and key points across all provided summaries."
#         ),
#     ]
# )
