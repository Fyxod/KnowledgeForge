from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from core.models.gpu_config import GPULLMConfig
from langchain_core.messages import BaseMessage
from core.llm.outputs import ChunksUsed
from core.constants import *


class AgentState(BaseModel):
    user_id: str
    thread_id: str
    query: str
    resolved_query: str
    original_query: str
    messages: List[BaseMessage]

    chunks: List[Dict[str, Any]] = Field(default_factory=list)
    web_search: bool = False
    web_search_queries: List[str] = Field(default_factory=list)
    web_search_results: List[Dict[str, Any]] = Field(default_factory=list)
    document_id: Optional[str] = None  # if using document_summarizer
    after_summary: Optional[Literal[f"{ANSWER}", f"{GENERATE}"]] = Field(
        default=f"{GENERATE}", description="The action to be taken after summarization."
    )

    summary: Optional[str] = None

    answer: Optional[str] = None
    chunks_used: List[ChunksUsed] = Field(default_factory=list)

    attempts: int = 0
    web_search_attempts: int = 0

    action: Optional[
        Literal[
            f"{ANSWER}",
            f"{WEB_SEARCH}",
            f"{DOCUMENT_SUMMARIZER}",
            f"{GLOBAL_SUMMARIZER}",
            f"{FAILURE}",
        ]
    ] = Field(
        default=None,
        description="The action to be taken by the agent. Can be 'answer', 'web_search', 'document_summarizer', 'global_summarizer', or 'failure'.",
    )

    # Used to determine the next step in the state graph
    next: Optional[str] = None
    llm: Optional[GPULLMConfig] = Field(
        default=None, description="The model to be used for the agent."
    )  # add more validation
    mode: Literal[f"{INTERNAL}", f"{EXTERNAL}"] = Field(
        description="The mode of the agent, either 'Internal' or 'External'."
    )
    initial_search_answer: Optional[str] = None  # to store initial web search answer
    initial_search_results: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # to store initial web search results
    use_self_knowledge: bool = False
