"""
Test data factories for generating consistent, realistic test objects.

Uses factory_boy + faker for deterministic test data generation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from faker import Faker

fake = Faker()
Faker.seed(42)  # Deterministic


# ---------------------------------------------------------------------------
# Primitive builders
# ---------------------------------------------------------------------------
def make_user_id() -> str:
    return f"user_{uuid4().hex[:8]}"


def make_thread_id() -> str:
    return f"thread_{uuid4().hex[:8]}"


def make_doc_id() -> str:
    return f"doc_{uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Document factories
# ---------------------------------------------------------------------------
def make_thread_document(
    doc_id: Optional[str] = None,
    title: Optional[str] = None,
    doc_type: str = "pdf",
    file_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "docId": doc_id or make_doc_id(),
        "title": title or fake.sentence(nb_words=4),
        "type": doc_type,
        "time_uploaded": datetime.now(timezone.utc),
        "file_name": file_name or f"{fake.word()}.{doc_type}",
    }


def make_chat_message(
    msg_type: str = "user",
    content: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "type": msg_type,
        "content": content or fake.paragraph(),
        "timestamp": datetime.now(timezone.utc),
    }


def make_instruction(
    text: Optional[str] = None,
    selected: bool = False,
) -> Dict[str, Any]:
    return {
        "id": uuid4().hex[:8],
        "text": text or fake.sentence(),
        "selected": selected,
    }


def make_thread(
    name: Optional[str] = None,
    documents: Optional[List[Dict]] = None,
    chats: Optional[List[Dict]] = None,
    instructions: Optional[List[Dict]] = None,
    extra_done: bool = False,
) -> Dict[str, Any]:
    return {
        "thread_name": name or f"Thread {fake.word()}",
        "documents": documents or [],
        "chats": chats or [],
        "instructions": instructions or [],
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "extra_done": extra_done,
    }


def make_user(
    user_id: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    password: str = "$2b$12$fakehashed",
    threads: Optional[Dict[str, Dict]] = None,
) -> Dict[str, Any]:
    return {
        "userId": user_id or make_user_id(),
        "name": name or fake.name(),
        "email": email or fake.email(),
        "password": password,
        "is_active": True,
        "threads": threads or {},
    }


# ---------------------------------------------------------------------------
# Document model factories (for core.models.document)
# ---------------------------------------------------------------------------
def make_page(number: int = 1, text: Optional[str] = None) -> Dict[str, Any]:
    return {
        "number": number,
        "text": text or fake.paragraph(nb_sentences=5),
        "images": [],
    }


def make_document_model(
    doc_id: Optional[str] = None,
    doc_type: str = "pdf",
    file_name: Optional[str] = None,
    title: Optional[str] = None,
    pages: int = 3,
    full_text: Optional[str] = None,
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    page_list = [make_page(i + 1) for i in range(pages)]
    return {
        "id": doc_id or make_doc_id(),
        "type": doc_type,
        "file_name": file_name or f"{fake.word()}.{doc_type}",
        "content": page_list,
        "title": title or fake.sentence(nb_words=4),
        "full_text": full_text or " ".join(p["text"] for p in page_list),
        "summary": summary,
        "has_sql_data": False,
        "spreadsheet_schema": None,
    }


def make_documents_model(
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    doc_count: int = 2,
) -> Dict[str, Any]:
    return {
        "documents": [make_document_model() for _ in range(doc_count)],
        "thread_id": thread_id or make_thread_id(),
        "user_id": user_id or make_user_id(),
    }


# ---------------------------------------------------------------------------
# Agent state factories
# ---------------------------------------------------------------------------
def make_agent_state_dict(
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    query: str = "What is the main topic?",
    mode: str = "External",
) -> Dict[str, Any]:
    return {
        "user_id": user_id or make_user_id(),
        "thread_id": thread_id or make_thread_id(),
        "query": query,
        "resolved_query": query,
        "original_query": query,
        "messages": [],
        "chunks": [],
        "web_search": False,
        "web_search_queries": [],
        "web_search_results": [],
        "document_id": None,
        "after_summary": "generate",
        "summary": None,
        "answer": None,
        "chunks_used": [],
        "confidence_score": None,
        "suggested_questions": None,
        "attempts": 0,
        "web_search_attempts": 0,
        "sql_query": None,
        "sql_result": None,
        "sql_attempts": 0,
        "has_spreadsheet_data": False,
        "spreadsheet_schema": None,
        "action": None,
        "next": None,
        "llm": {"model": "test-model", "port": 11434},
        "mode": mode,
        "initial_search_answer": None,
        "initial_search_results": [],
        "use_self_knowledge": False,
        "thread_instructions": [],
    }


# ---------------------------------------------------------------------------
# LLM output factories
# ---------------------------------------------------------------------------
def make_decomposition_output(
    requires_decomposition: bool = False,
    resolved_query: str = "What is the main topic?",
    sub_queries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "requires_decomposition": requires_decomposition,
        "resolved_query": resolved_query,
        "sub_queries": sub_queries or [],
    }


def make_combination_output(answer: str = "Combined answer") -> Dict[str, Any]:
    return {"answer": answer}


def make_main_llm_output(
    answer: str = "Test answer",
    action: str = "answer",
    chunks_used: Optional[List] = None,
    suggested_questions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "answer": answer,
        "action": action,
        "chunks_used": chunks_used or [],
        "document_id": None,
        "suggested_questions": suggested_questions or ["Follow-up question?"],
        "web_search_queries": [],
    }
