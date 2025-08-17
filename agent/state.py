from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage
from core.llm.outputs import DocumentsUsed
from core.constants import *

class AgentState(BaseModel):
    user_id: str
    thread_id: str
    question: str
    original_question: str
    messages: List[BaseMessage]

    documents: List[Dict[str, Any]] = Field(default_factory=list)
    web_search: bool = False
    search_queries: List[str] = Field(default_factory=list)
    search_queries_results: List[Dict[str, Any]] = Field(default_factory=list)
    document_id: Optional[str] = None # if using document_summarizer
    after_summary: Optional[Literal[f"{ANSWER}", f"{GENERATE}", f"{DOCUMENT_SUMMARIZER}", f"{GLOBAL_SUMMARIZER}"]] = Field(
        default=f"{GENERATE}",
        description="The action to be taken after summarization."
    )

    summary: Optional[str] = None
    
    answer: Optional[str] = None
    documents_used: List[DocumentsUsed] = Field(default_factory=list)

    attempts: int = 0
    web_search_attempts: int = 0

    action: Optional[Literal[f"{ANSWER}", f"{WEB_SEARCH}", f"{DOCUMENT_SUMMARIZER}", f"{GLOBAL_SUMMARIZER}"]] = Field(
        default=None,
        description="The action to be taken by the agent. Can be 'answer', 'web_search', 'document_summarizer', or 'global_summarizer'."
    )
    retrieval_query: Optional[str] = None

    # Used to determine the next step in the state graph
    next: Optional[str] = None
