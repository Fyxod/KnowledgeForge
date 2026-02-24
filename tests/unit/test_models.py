"""
Unit tests for Pydantic models — User, Document, Thread, GPUConfig models.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestUserCreateModel:
    def test_valid_creation(self):
        from core.models.user import UserCreateModel

        user = UserCreateModel(name="Test", email="test@test.com", password="pass123")
        assert user.name == "Test"
        assert user.email == "test@test.com"

    def test_invalid_email_raises(self):
        from core.models.user import UserCreateModel

        with pytest.raises(ValidationError):
            UserCreateModel(name="Test", email="not-an-email", password="pass123")

    def test_missing_password_raises(self):
        from core.models.user import UserCreateModel

        with pytest.raises(ValidationError):
            UserCreateModel(name="Test", email="test@test.com")


@pytest.mark.unit
class TestUserLoginModel:
    def test_valid_login(self):
        from core.models.user import UserLoginModel

        login = UserLoginModel(email="test@test.com", password="pass")
        assert login.email == "test@test.com"

    def test_invalid_email_raises(self):
        from core.models.user import UserLoginModel

        with pytest.raises(ValidationError):
            UserLoginModel(email="bad", password="pass")


@pytest.mark.unit
class TestUserJwtPayload:
    def test_valid_payload(self):
        from core.models.user import UserJwtPayload

        p = UserJwtPayload(userId="u1", name="Test", email="t@t.com")
        assert p.userId == "u1"
        assert p.is_active is True  # default

    def test_inactive_user(self):
        from core.models.user import UserJwtPayload

        p = UserJwtPayload(userId="u1", name="Test", email="t@t.com", is_active=False)
        assert p.is_active is False


@pytest.mark.unit
class TestThreadDocument:
    def test_valid_document(self):
        from core.models.user import ThreadDocument

        doc = ThreadDocument(
            docId="d1",
            title="Doc",
            type="pdf",
            time_uploaded=datetime.now(timezone.utc),
            file_name="test.pdf",
        )
        assert doc.docId == "d1"

    def test_missing_fields_raises(self):
        from core.models.user import ThreadDocument

        with pytest.raises(ValidationError):
            ThreadDocument(docId="d1")


@pytest.mark.unit
class TestChatMessage:
    def test_valid_user_message(self):
        from core.models.user import ChatMessage

        msg = ChatMessage(
            type="user", content="Hello", timestamp=datetime.now(timezone.utc)
        )
        assert msg.type == "user"

    def test_valid_agent_message(self):
        from core.models.user import ChatMessage

        msg = ChatMessage(
            type="agent", content="Hi", timestamp=datetime.now(timezone.utc)
        )
        assert msg.type == "agent"

    def test_invalid_type_raises(self):
        from core.models.user import ChatMessage

        with pytest.raises(ValidationError):
            ChatMessage(
                type="system", content="X", timestamp=datetime.now(timezone.utc)
            )


@pytest.mark.unit
class TestDocumentModel:
    def test_valid_document(self):
        from core.models.document import Document

        doc = Document(
            id="d1",
            type="pdf",
            file_name="test.pdf",
            title="Test",
            full_text="Some text",
        )
        assert doc.id == "d1"
        assert doc.has_sql_data is False
        assert doc.summary is None

    def test_with_pages(self):
        from core.models.document import Document, Page

        page = Page(number=1, text="Page content")
        doc = Document(
            id="d1",
            type="pdf",
            file_name="test.pdf",
            title="Test",
            full_text="Page content",
            content=[page],
        )
        assert len(doc.content) == 1
        assert doc.content[0].number == 1

    def test_with_sql_data(self):
        from core.models.document import Document

        doc = Document(
            id="d1",
            type="xlsx",
            file_name="data.xlsx",
            title="Sheet",
            full_text="data",
            has_sql_data=True,
            spreadsheet_schema="CREATE TABLE...",
        )
        assert doc.has_sql_data is True


@pytest.mark.unit
class TestDocumentsModel:
    def test_valid(self):
        from core.models.document import Documents

        docs = Documents(documents=[], thread_id="t1", user_id="u1")
        assert docs.thread_id == "t1"
        assert len(docs.documents) == 0


@pytest.mark.unit
class TestPageModel:
    def test_valid_page(self):
        from core.models.document import Page

        p = Page(number=1, text="Hello")
        assert p.number == 1
        assert p.images == []

    def test_page_with_images(self):
        from core.models.document import Page

        p = Page(number=1, text="Hello", images=["img1.png", "img2.png"])
        assert len(p.images) == 2


@pytest.mark.unit
class TestGPULLMConfig:
    def test_valid_config(self):
        from core.models.gpu_config import GPULLMConfig

        config = GPULLMConfig(model="qwen3:14b", port=11434)
        assert config.model == "qwen3:14b"
        assert config.port == 11434


@pytest.mark.unit
class TestThreadModels:
    def test_thread_create_request_default(self):
        from core.models.thread import ThreadCreateRequest

        req = ThreadCreateRequest()
        assert req.thread_name == "New Chat"

    def test_thread_create_request_custom(self):
        from core.models.thread import ThreadCreateRequest

        req = ThreadCreateRequest(thread_name="My Thread")
        assert req.thread_name == "My Thread"

    def test_thread_update_request(self):
        from core.models.thread import ThreadUpdateRequest

        req = ThreadUpdateRequest(thread_name="Renamed")
        assert req.thread_name == "Renamed"

    def test_instruction_create_request(self):
        from core.models.thread import InstructionCreateRequest

        req = InstructionCreateRequest(text="Be concise")
        assert req.text == "Be concise"

    def test_instruction_update_request_partial(self):
        from core.models.thread import InstructionUpdateRequest

        req = InstructionUpdateRequest(selected=True)
        assert req.selected is True
        assert req.text is None

    def test_add_existing_document_request(self):
        from core.models.thread import AddExistingDocumentRequest

        req = AddExistingDocumentRequest(source_thread_id="t1", doc_id="d1")
        assert req.source_thread_id == "t1"
