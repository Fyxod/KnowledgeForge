from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class ChunksUsed(BaseModel):
    document_id: str = Field(
        description="The ID of the document used to which the chunk belongs."
    )
    page_no: int = Field(description="The page_no of the document used.")


class MainLLMOutputInternal(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal[
        "answer",
        "document_summarizer",  # requires document id of the document to summarize
        "global_summarizer",
    ] = Field(description="The action to take based on the answer.")
    chunks_used: Optional[List[ChunksUsed]] = Field(
        default=None,
        description="List of chunks used to generate the answer, if applicable.",
    )
    document_id: Optional[str] = Field(
        description="The ID of the document to summarize if using document_summarizer, if applicable."
    )


class MainLLMOutputInternalWithFailure(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal[
        "answer",
        "document_summarizer",  # requires document id of the document to summarize
        "global_summarizer",
        "failure",
    ] = Field(description="The action to take based on the answer.")
    chunks_used: Optional[List[ChunksUsed]] = Field(
        default=None,
        description="List of chunks used to generate the answer, if applicable.",
    )
    document_id: Optional[str] = Field(
        description="The ID of the document to summarize if using document_summarizer, if applicable."
    )


class MainLLMOutputExternal(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal[
        "answer",
        "web_search",
        "document_summarizer",  # requires document id of the document to summarize
        "global_summarizer",
        "failure",
    ] = Field(description="The action to take based on the answer.")
    chunks_used: Optional[List[ChunksUsed]] = Field(
        default=None,
        description="List of chunks used to generate the answer, if applicable.",
    )
    web_search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of 2-3 web search queries used to generate the answer, if applicable.",
    )
    document_id: Optional[str] = Field(
        description="The ID of the document to summarize if using document_summarizer, if applicable."
    )


class SelfKnowledgeLLMOutput(BaseModel):
    answer: str = Field(description="The answer to the user's question.")


class DecompositionLLMOutput(BaseModel):
    requires_decomposition: bool = Field(
        description="Indicates whether the query requires decomposition."
    )
    resolved_query: str = Field(
        description="The resolved query after context resolution."
    )
    sub_queries: List[str] = Field(
        description="List of standalone sub-queries generated from the original query."
    )


class CombinationLLMOutput(BaseModel):
    answer: str = Field(description="The combined answer from multiple sub-answers.")
