from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage
from core.llm.outputs import DocumentsUsed


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

    answer: Optional[str] = None
    documents_used: List[DocumentsUsed] = Field(default_factory=list)

    attempts: int = 0
    web_search_attempts: int = 0

    action: Optional[Literal["answer", "web_search", "document_summarizer", "global_summarizer"]] = None
    retrieval_query: Optional[str] = None

    # Used to determine the next step in the state graph
    next: Optional[str] = None
