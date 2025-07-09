from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessage,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

rewrite_query_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant tasked with rewriting user messages for semantic vector search. "
                "Your job is to convert a potentially vague or follow-up question into a clear, standalone query that can be used for document retrieval. "
                "Preserve the user's intent without adding new information."
            )
        ),
        SystemMessage(
            content=(
                "If the user's message already makes sense on its own, return it unchanged. "
                "If the message is ambiguous, contains spelling errors, or appears to reference previous assistant responses, use the previous turn to clarify it."
                "Fix small typos and normalize the message if necessary."
            )
        ),
        SystemMessage(
            content=(
                "The goal is to maximize the relevance and specificity of the query for use with a vector-based semantic search engine."
            )
        ),
        MessagesPlaceholder(variable_name="recent_history"),
        HumanMessagePromptTemplate.from_template(
            "User's current message: {question}\n\nRewritten query for semantic search:"
        ),
    ]
)
