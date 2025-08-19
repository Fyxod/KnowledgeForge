from typing import Any, Dict, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import (
    MessagesPlaceholder,
)


def main_prompt(
    messages: list,
    documents: str,
    question: str,
    summary: str,
    search_queries_results: List[Dict[str, Any]],
):
    """
    Builds the main prompt for the agent in Gemini format (contents list).
    """

    contents = []

    # System instruction
    contents.append(
        {
            "role": "system",
            "parts": (
                "You are a helpful assistant that answers questions based on the provided documents. "
                "Use the retrieved context to give the best possible answer. "
                "Extract and use as much relevant information as possible from the documents. "
                "If the question is answerable using the provided documents, provide a direct, specific and detailed answer using relevant details. "
                "Only if the question truly cannot be answered using the documents and your own knowledge, then ask for clarification or suggest a web search or use summarizers accordingly. "
                "Do not default to asking for clarification if relevant information is available in the context.\n\n"
                "You also have access to these tools if needed:\n"
                "- `answer`: Use this if you can directly answer the question.\n"
                "- `web_search`: Use this if you need more recent or external information not available in the documents.\n"
                "- `document_summarizer`: Use this if you need the summary of a specific document for answering the user's question. You must provide the `document_id`.\n"
                "- `global_summarizer`: Use this if you need a collective summary of all the documents for any question.\n"
                "If the user asks for a summary, give `document_summarizer` or `global_summarizer` as action accordingly."
            ),
        }
    )

    # Retrieved context
    contents.append(
        {
            "role": "system",
            "parts": f"Here is the retrieved context according to the question:\n{documents}",
        }
    )

    # Optional summary
    if summary:
        contents.append(
            {
                "role": "system",
                "parts": f"This is the summary that you asked for. Use this accordingly to answer the user's question:\n{summary}",
            }
        )

    # Optional web search results
    if search_queries_results:
        contents.append(
            {
                "role": "system",
                "parts": f"Here are the web search queries results:\n{search_queries_results}",
            }
        )

    # Conversation history
    for m in messages:
        if m.type == "human":
            contents.append({"role": "user", "parts": m.content})
        elif m.type == "ai":
            contents.append({"role": "assistant", "parts": m.content})

    # Final user question
    contents.append({"role": "user", "parts": question})

    return contents


# def main_prompt(
#     messages: list,
#     documents: str,
#     question: str,
#     summary: str,
#     search_queries_results: List[Dict[str, Any]],
# ):
#     """
#     Builds the main prompt for the agent based on the current state.
#     """

#     messages_array = [
#         SystemMessage(
#             content=(
#                 "You are a helpful assistant that answers questions based on the provided documents. "
#                 # "Use the retrieved context to provide the most accurate, direct, and specific answer possible. "
#                 "Use the retrieved context to give the best possible answer. "
#                 "Extract and use as much relevant information as possible from the documents. "
#                 "If the question is answerable using the provided documents, provide a direct, specific and detailed answer using relevant details."
#                 "Only if the question truly cannot be answered using the documents and your own knowledge, then ask for clarification or suggest a web search or use summarizers accordingly. "
#                 "Do not default to asking for clarification if relevant information is available in the context."
#                 "\n\n"
#                 "You also have access to these tools if needed:\n"
#                 "- `answer`: Use this if you can directly answer the question.\n"
#                 "- `web_search`: Use this if you need more recent or external information not available in the documents.\n"
#                 "- `document_summarizer`: Use this if you need the summary of a specific document for answering the user's question. You must provide the `document_id`.\n"
#                 "- `global_summarizer`: Use this if you need a collective summary of all the documents for any question."
#                 "If the user asks for a summary, give `document_summarizer` or `global_summarizer` as action accordingly."
#             )
#         ),
#         MessagesPlaceholder(variable_name="messages"),
#         SystemMessage(
#             content=f"Here is the retrieved context according to the question:\n{documents}"
#         ),
#     ]
#     if summary:
#         messages_array.append(SystemMessage(content=f"This is the summary that the you asked for. Use this accordingly to answer the user's question: {summary}\n\n"))

#     if search_queries_results:
#         messages_array.append(
#             SystemMessage(
#                 content=f"Here are the web search queries results:\n{search_queries_results}"
#             )
#         )

#     messages_array.append(HumanMessage(content=question))

#     prompt = ChatPromptTemplate.from_messages(messages_array)
#     return prompt.format_messages(
#         messages=messages,
#     )


# def main_prompt(
#     messages: list,
#     documents: str,
#     question: str,
#     summary: str,
#     search_queries_results: List[Dict[str, Any]],
# ):
#     """
#     Builds the main prompt for the agent based on the current state.
#     This prompt allows the LLM to use its internal knowledge as a fallback.
#     """

#     # This system prompt establishes a clear hierarchy of information sources:
#     # 1. Documents -> 2. Web Search -> 3. Internal Knowledge.
#     # It instructs the model on how to act when information is in one source but not another.
#     system_prompt = """
# You are a highly capable AI research assistant. Your primary goal is to provide the most accurate and comprehensive answer possible by intelligently combining information from three sources in this order of priority:
# 1.  **Provided Context**: `Retrieved Context` from documents and any provided `Summary`.
# 2.  **Web Search Results**: Real-time information from the `web_search` tool.
# 3.  **Your Own Internal Knowledge**: Your general pre-trained knowledge base.

# **Your Thought Process:**
# 1.  **Analyze the Question**: Understand exactly what the user is asking.
# 2.  **Consult Sources in Order**:
#     - First, always check the `Retrieved Context`. If it contains a complete answer, base your response primarily on it.
#     - If the context is insufficient, check the `Web Search Results`.
#     - If there is still no definitive answer, you may use your **own internal knowledge**, but only if you are confident in the information.
# 3.  **Synthesize the Answer**: Combine information from these sources to construct the best possible response.

# **Critical Rules:**
# - **Source Priority is Key**: The `Retrieved Context` is the highest authority. If your internal knowledge conflicts with the provided documents, you **MUST** prioritize the information from the documents.
# - **Be Transparent About Your Sources**: When possible, let the user know where the information is coming from. For example: "According to the document [document name/ID if available], ...", or "The provided context does not cover this, but based on my general knowledge...".
# - **Use Tools Intelligently**:
#     - **`web_search`**: Use this tool only if the documents are insufficient AND the question requires information you are not confident about (e.g., very recent events, specific statistics, breaking news). Do not use it for general knowledge questions you can already answer.
#     - **`document_summarizer` / `global_summarizer`**: Use these only when the user explicitly asks for a summary or you need it to answer any question.
# - **NEVER Invent Information**: If you cannot answer the question from any of the available sources (documents, web search, or your own confident knowledge), state that you are unable to find the answer. Do not create false information.
# - **Be Direct and Comprehensive**: Get straight to the point and use Markdown for readability.
# """

#     messages_array = [
#         SystemMessage(content=system_prompt),
#         MessagesPlaceholder(variable_name="messages"),
#     ]

#     context_parts = []
#     if documents:
#         context_parts.append(f"### Retrieved Context:\n{documents}")
#     if summary:
#         context_parts.append(f"### Requested Summary:\n{summary}")
#     if search_queries_results:
#         formatted_results = "\n\n".join(
#             [
#                 f"Query: {res['query']}\nResult: {res['results']}"
#                 for res in search_queries_results
#             ]
#         )
#         context_parts.append(f"### Web Search Results:\n{formatted_results}")

#     if context_parts:
#         messages_array.append(HumanMessage(content="\n\n".join(context_parts)))

#     messages_array.append(HumanMessage(content=f"Question: {question}"))

#     prompt = ChatPromptTemplate.from_messages(messages_array)

#     return prompt.format_messages(
#         messages=messages,
#     )
