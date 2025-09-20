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

        # System instruction
        contents.append(
            {
                "role": "system",
                "parts": (
                    "You are a helpful assistant that answers questions based on the provided documents. "
                    "Use the retrieved context to give the best possible answer. "
                    "Extract and use as much relevant information as possible from the documents. "
                    "If the question is answerable using the provided documents, provide a direct, specific and detailed answer using relevant details. "
                    "Only if the question truly cannot be answered using the documents and your own knowledge, then ask for clarification or use summarizers accordingly. "
                    "Do not default to asking for clarification if relevant information is available in the context.\n\n"
                    "You also have access to these tools if needed:\n"
                    "- `answer`: Use this if you can directly answer the question.\n"
                    "- `document_summarizer`: Use this if you need the summary of a specific document for answering the user's question. You must provide the `document_id`.\n"
                    "- `global_summarizer`: Use this if you need a collective summary of all the documents for any question.\n"
                    "If the user asks for a summary, give `document_summarizer` or `global_summarizer` as action accordingly.\n"
                    "Give your final answer in clear, structured Markdown format for readability.\n"
                ),
            }
        )

        # Retrieved context
        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f"Documents chunks from which you must try to answer the question:\n{chunks}\n",
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
                    "parts": f"This is the summary that you asked for. Use this accordingly to answer the user's question:\n{summary}\n",
                }
            )

        
    elif mode == "External":

        # System instruction
        contents.append(
            {
                "role": "system",
                "parts": (
                    "You are a helpful assistant that answers questions based on the provided documents. "
                    "Use the retrieved context to give the best possible answer. "
                    "Extract and use as much relevant information as possible from the documents. "
                    "If the question is answerable using the provided documents, provide a direct, clear and detailed answer using relevant details. "
                    "Only if the question truly cannot be answered using the documents and your own knowledge, then ask for clarification or suggest a web search or use summarizers accordingly. "
                    "Do not default to asking for clarification if relevant information is available in the context.\n\n"
                    "You also have access to these tools if needed:\n"
                    "- `answer`: Use this if you can directly answer the question.\n"
                    "- `web_search`: Use this if you need more recent or external information not available in the documents.\n"
                    "- `document_summarizer`: Use this if you need the summary of a specific document for answering the user's question. You must provide the `document_id`.\n"
                    "- `global_summarizer`: Use this if you need a collective summary of all the documents for any question.\n"
                    "If the user asks for a summary, give `document_summarizer` or `global_summarizer` as action accordingly.\n"
                    "Give long detailed structured responses unless asked otherwise\n"
                    "Give your final answer in clear, structured Markdown format for readability.\n"
                ),
            }
        )

        # Retrieved context
        if chunks:
            contents.append(
                {
                    "role": "system",
                    "parts": f"Documents chunks from which you must try to answer the question:\n{chunks}\n",
                }
            )
        if initial_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"Additional external knowledge that might be useful to answer the question: {initial_search_results}\n",
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
                    "parts": f"This is the summary that you asked for. Use this accordingly to answer the user's question:\n{summary}\n",
                }
            )

        # Optional web search results
        if web_search_results:
            contents.append(
                {
                    "role": "system",
                    "parts": f"Here are the web search queries results that you asked for in the previous iteration:\n{web_search_results}\n",
                }
            )

        if initial_search_answer:
            contents.append(
                {
                    "role": "system",
                    "parts": f"Initial web search answer that might be useful to answer the question: {initial_search_answer}\n",
                }
            )
        contents.append(
            {
                "role": "system",
                "parts": "If conflicted information is present, prioritise the document information over web search results.",
            }
        )
        

        # Final user question
    else:
        raise ValueError("Invalid mode. Mode must be either 'Internal' or 'External'.")
    
    contents.append({"role": "user", "parts": f"Question: {question}\n"})
    # ask to return correct json
    contents.append({"role": "user", "parts": "Please return the response in the correct JSON format."})
    return contents
