"""
Additional unit tests for core.embeddings.vectorstore to cover uncovered code paths.
Tests for: save_documents_to_store, add_existing_document_to_store, chunk_page_text (NLTK path).
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
class TestSaveDocumentsToStore:
    @pytest.mark.asyncio
    async def test_save_documents(self):
        from core.embeddings.vectorstore import save_documents_to_store
        from core.models.document import Document, Page, Documents

        page = Page(number=1, text="Hello world content")
        doc = Document(
            id="d1",
            type="pdf",
            file_name="test.pdf",
            title="Test",
            full_text="Hello world content",
            content=[page],
        )
        docs = Documents(documents=[doc], user_id="u1", thread_id="t1")

        mock_vs = MagicMock()
        mock_vs._collection.upsert = MagicMock()
        mock_vs.embeddings.embed_documents = MagicMock(return_value=[[0.1] * 768])

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with (
            patch("core.embeddings.vectorstore.get_vectorstore", return_value=mock_vs),
            patch("core.embeddings.vectorstore._build_and_save_bm25"),
            patch(
                "core.embeddings.vectorstore.asyncio.to_thread",
                side_effect=fake_to_thread,
            ),
        ):
            await save_documents_to_store(docs, "u1", "t1")

    @pytest.mark.asyncio
    async def test_save_documents_empty(self):
        from core.embeddings.vectorstore import save_documents_to_store
        from core.models.document import Document, Documents

        doc = Document(
            id="d1",
            type="pdf",
            file_name="test.pdf",
            title="Test",
            full_text="",
            content=[],
        )
        docs = Documents(documents=[doc], user_id="u1", thread_id="t1")

        mock_vs = MagicMock()

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with (
            patch("core.embeddings.vectorstore.get_vectorstore", return_value=mock_vs),
            patch("core.embeddings.vectorstore._build_and_save_bm25"),
            patch(
                "core.embeddings.vectorstore.asyncio.to_thread",
                side_effect=fake_to_thread,
            ),
        ):
            await save_documents_to_store(docs, "u1", "t1")


@pytest.mark.unit
class TestAddExistingDocumentToStore:
    @pytest.mark.asyncio
    async def test_add_existing_document(self):
        from core.embeddings.vectorstore import add_existing_document_to_store
        from core.models.document import Document, Page

        page = Page(number=1, text="Page one content here")
        doc = Document(
            id="d1",
            type="pdf",
            file_name="doc.pdf",
            title="Doc Title",
            full_text="Page one content here",
            content=[page],
        )

        mock_vs = MagicMock()
        mock_vs._collection.upsert = MagicMock()
        mock_vs.embeddings.embed_documents = MagicMock(return_value=[[0.1] * 768])

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with (
            patch("core.embeddings.vectorstore.get_vectorstore", return_value=mock_vs),
            patch("core.embeddings.vectorstore._build_and_save_bm25"),
            patch("core.embeddings.vectorstore.load_bm25", return_value=None),
            patch(
                "core.embeddings.vectorstore.asyncio.to_thread",
                side_effect=fake_to_thread,
            ),
        ):
            await add_existing_document_to_store(doc, "u1", "t1")

    @pytest.mark.asyncio
    async def test_add_existing_no_pages(self):
        from core.embeddings.vectorstore import add_existing_document_to_store
        from core.models.document import Document

        doc = Document(
            id="d1",
            type="pdf",
            file_name="doc.pdf",
            title="Doc Title",
            full_text="",
            content=[],
        )

        mock_vs = MagicMock()

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with (
            patch("core.embeddings.vectorstore.get_vectorstore", return_value=mock_vs),
            patch("core.embeddings.vectorstore._build_and_save_bm25"),
            patch("core.embeddings.vectorstore.load_bm25", return_value=None),
            patch(
                "core.embeddings.vectorstore.asyncio.to_thread",
                side_effect=fake_to_thread,
            ),
        ):
            await add_existing_document_to_store(doc, "u1", "t1")

    @pytest.mark.asyncio
    async def test_add_with_existing_bm25(self):
        from core.embeddings.vectorstore import add_existing_document_to_store
        from core.models.document import Document, Page

        page = Page(number=1, text="Page content text here")
        doc = Document(
            id="d1",
            type="pdf",
            file_name="doc.pdf",
            title="Test",
            full_text="Page content text here",
            content=[page],
        )

        mock_vs = MagicMock()
        mock_vs._collection.upsert = MagicMock()
        mock_vs.embeddings.embed_documents = MagicMock(return_value=[[0.1] * 768])

        existing_bm25 = {
            "chunk_ids": ["existing_1"],
            "chunk_texts": ["old chunk"],
            "chunk_metadatas": [{"document_id": "d0"}],
        }

        async def fake_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        with (
            patch("core.embeddings.vectorstore.get_vectorstore", return_value=mock_vs),
            patch("core.embeddings.vectorstore._build_and_save_bm25"),
            patch("core.embeddings.vectorstore.load_bm25", return_value=existing_bm25),
            patch(
                "core.embeddings.vectorstore.asyncio.to_thread",
                side_effect=fake_to_thread,
            ),
        ):
            await add_existing_document_to_store(doc, "u1", "t1")


@pytest.mark.unit
class TestChunkPageTextNltk:
    """Test chunk_page_text — returns List[str] of text chunks."""

    def test_multisentence_text(self):
        from core.embeddings.vectorstore import chunk_page_text

        text = "This is the first sentence. This is the second sentence. And a third one for good measure."
        chunks = chunk_page_text(text)
        assert len(chunks) >= 1
        for chunk_text in chunks:
            assert isinstance(chunk_text, str)
            assert len(chunk_text) > 0

    def test_very_long_text(self):
        from core.embeddings.vectorstore import chunk_page_text

        text = "This is a test sentence. " * 500
        chunks = chunk_page_text(text)
        assert len(chunks) > 1

    def test_single_sentence(self):
        from core.embeddings.vectorstore import chunk_page_text

        text = "Just one sentence."
        chunks = chunk_page_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Just one sentence."


@pytest.mark.unit
class TestGetVectorstoreDetailed:
    def test_creates_vectorstore(self):
        from core.embeddings.vectorstore import get_vectorstore

        mock_chroma = MagicMock()
        mock_embed = MagicMock()

        with (
            patch("core.embeddings.vectorstore.Chroma", return_value=mock_chroma),
            patch(
                "core.embeddings.vectorstore.get_embedding_function",
                return_value=mock_embed,
            ),
        ):
            result = get_vectorstore("user1", "thread1")

        assert result is mock_chroma
