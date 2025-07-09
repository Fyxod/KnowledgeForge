from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional, Any
from langchain_core.messages import BaseMessage


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
    answer: Optional[str] = None
    documents_used: List[str] = Field(default_factory=list)
    attempts: int = 0
    web_search_attempts: int = 0
    action: Optional[Literal["answer", "web_search"]] = None
    retrieval_query: Optional[str] = None
    # This is used to determine the next step in the state graph
    next: Optional[str] = None
