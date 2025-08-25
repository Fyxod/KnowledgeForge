from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class DocumentsUsed(BaseModel):
    document_id: str = Field(description="The ID of the document used.")
    # title: str = Field(description="The title of the document used.")
    page_no: int = Field(description="The page_no of the document used.")
    chunk_index: int = Field(description="The chunk_index used from the document.")


class MainLLMOutput(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal[
        "answer",
        "web_search",
        "document_summarizer",  # requires document id of the document to summarize
        "global_summarizer",
    ] = Field(description="The action to take based on the answer.")
    documents_used: Optional[List[DocumentsUsed]] = Field(
        default=None,
        description="List of documents used to generate the answer, if applicable.",
    )
    web_search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of 2-3 web search queries used to generate the answer, if applicable.",
    )
    document_id: Optional[str] = Field(
        description="The ID of the document to summarize if using document_summarizer, if applicable."
    )


class REWRITELLMOutput(BaseModel):
    rewritten_query: str = Field(
        description="The rewritten query for semantic vector search based on the user's message."
    )


class SummarizerLLMOutputSingle(BaseModel):
    document_id: str = Field(description="The ID of the document that was summarized.")
    summary: str = Field(description="The summary of the document.")


class SummarizerLLMOutput(BaseModel):
    summaries: List[SummarizerLLMOutputSingle] = Field(
        description="List of summaries for each document."
    )


class GlobalSummarizerLLMOutput(BaseModel):
    title: str = Field(
        description="A concise and descriptive title for the collection of documents."
    )
    summary: str = Field(
        description="The global summary of all provided document summaries."
    )


class Node(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: List["Node"] = []

    class Config:
        arbitrary_types_allowed = True


class FlatNode(BaseModel):
    id: str
    title: str
    parent_id: Optional[str] = None


class MindMapOutput(BaseModel):
    output: List[FlatNode] = Field(description="The generated mind map structure.")


class FlatNodeWithDescription(BaseModel):
    id: str
    title: str
    description: str


class FlatNodeWithDescriptionOutput(BaseModel):
    output: List[FlatNodeWithDescription]


class MindMap(BaseModel):
    user_id: str
    thread_id: str
    document_id: str
    roots: List[Node]
