from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessage,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)


main_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant that answers questions based on the provided documents. "
                "Use the retrieved context to give the best possible answer. "
                "If the question is answerable using the provided documents, provide a direct and specific answer using relevant details."
            )
        ),
        SystemMessage(
            content=(
                "Only if the question truly cannot be answered using the documents, then ask for clarification or suggest a web search. "
                "Do not default to asking for clarification if relevant information is available in the context."
            )
        ),
        MessagesPlaceholder(variable_name="messages"),
        HumanMessagePromptTemplate.from_template(
            "Here is the retrieved context according to the question:\n{documents}"
        ),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)
