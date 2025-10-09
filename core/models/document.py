from pydantic import BaseModel, Field
from typing import Optional, List


class Page(BaseModel):
    number: int
    text: str
    images: Optional[List[str]] = Field(default_factory=list)


class Document(BaseModel):
    id: str
    type: str
    file_name: str
    content: List[Page] = Field(default_factory=list)
    title: str
    full_text: str
    summary: Optional[str] = None


class Documents(BaseModel):
    documents: List[Document] = Field(default_factory=list)
    thread_id: str
    user_id: str
