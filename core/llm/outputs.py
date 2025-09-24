from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChunksUsed(BaseModel):
    document_id: str = Field(
        description="The ID of the document used to which the chunk belongs."
    )
    # title: str = Field(description="The title of the document used.")
    page_no: int = Field(description="The page_no of the document used.")
    chunk_index: int = Field(description="The chunk_index used from the document.")


class MainLLMOutputInternal(BaseModel):
    answer: str = Field(description="The answer to the user's question.")


class MainLLMOutputExternal(BaseModel):
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


class SummarizerLLMOutputSingle(BaseModel):
    document_id: str = Field(description="The ID of the document that was summarized.")
    summary: str = Field(description="The summary of the document.")


class SummarizerLLMOutputCombination(BaseModel):
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
    mind_map: List[FlatNode] = Field(description="The generated mind map structure.")


class FlatNodeWithDescription(BaseModel):
    id: str
    title: str
    description: str


class FlatNodeWithDescriptionOutput(BaseModel):
    mind_map: List[FlatNodeWithDescription]


class MindMap(BaseModel):
    user_id: str
    thread_id: str
    document_id: str
    roots: List[Node]


class GlobalMindMap(BaseModel):
    user_id: str
    thread_id: str
    roots: List[Node]
