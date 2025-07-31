from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)


main_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You are a helpful assistant that answers questions based on the provided documents. "
                # "Use the retrieved context to provide the most accurate, direct, and specific answer possible. "
                "Use the retrieved context to give the best possible answer. "
                "Extract and use as much relevant information as possible from the documents. "
                "If the question is answerable using the provided documents, provide a direct, specific and detailed answer using relevant details."
                "Only if the question truly cannot be answered using the documents and your own knowledge, then ask for clarification or suggest a web search. "
                "Do not default to asking for clarification if relevant information is available in the context."
                "\n\n"
                "You also have access to these tools if needed:\n"
                "- `answer`: Use this if you can directly answer the question.\n"
                "- `web_search`: Use this if you need more recent or external information not available in the documents.\n"
                "- `document_summarizer`: Use this if you need the summary of a specific document. You must provide the `document_id`.\n"
                "- `global_summarizer`: Use this if you need a collective summary of all the documents.\n\n"
            )
        ),
        MessagesPlaceholder(variable_name="messages"),
        HumanMessagePromptTemplate.from_template(
            "Here is the retrieved context according to the question:\n{documents}"
        ),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)
