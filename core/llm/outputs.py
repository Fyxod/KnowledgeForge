from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class MainLLMOutput(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    action: Literal["answer", "web_search"] = Field(
        description="The action to take based on the answer."
    )
    documents_used: Optional[List[str]] = Field(
        default=None,
        description="List of document ids of documents used to generate the answer, if applicable.",
    )
    web_search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of 2-3 web search queries used to generate the answer, if applicable.",
    )


class REWRITELLMOutput(BaseModel):
    rewritten_query: str = Field(
        description="The rewritten query for semantic vector search based on the user's message."
    )
