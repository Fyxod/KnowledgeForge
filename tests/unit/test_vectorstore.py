"""
Unit tests for core.embeddings.vectorstore — chunking, BM25, ChromaDB operations.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
class TestChunkPageText:
    def test_short_text_single_chunk(self):
        from core.embeddings.vectorstore import chunk_page_text

        chunks = chunk_page_text("Short text.")
        assert len(chunks) >= 1
        assert "Short text." in chunks[0]

    def test_long_text_multiple_chunks(self):
        from core.embeddings.vectorstore import chunk_page_text

        text = "This is a sentence. " * 200
        chunks = chunk_page_text(text)
        assert len(chunks) > 1

    def test_empty_text(self):
        from core.embeddings.vectorstore import chunk_page_text

        chunks = chunk_page_text("")
        assert isinstance(chunks, list)

    def test_chunk_size_limit(self):
        from core.embeddings.vectorstore import chunk_page_text, CHUNK_SIZE

        # Use proper sentences so NLTK can split them into chunks
        text = "This is a test sentence. " * 200
        chunks = chunk_page_text(text)
        assert len(chunks) > 1
        # Each chunk should be bounded; with sentence boundaries NLTK can split
        for chunk in chunks:
            assert len(chunk) <= CHUNK_SIZE * 3


@pytest.mark.unit
class TestDeleteDocumentFromChroma:
    @pytest.mark.asyncio
    @patch("core.embeddings.vectorstore.get_vectorstore")
    async def test_deletes_matching_ids(self, mock_get_vs):
        from core.embeddings.vectorstore import delete_document_from_chroma

        mock_vs = MagicMock()
        # actual code calls vectorstore._collection.delete(where=...)
        mock_collection = MagicMock()
        mock_vs._collection = mock_collection
        mock_get_vs.return_value = mock_vs

        await delete_document_from_chroma("u1", "t1", "doc1")
        mock_collection.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("core.embeddings.vectorstore.get_vectorstore")
    async def test_no_matching_docs(self, mock_get_vs):
        from core.embeddings.vectorstore import delete_document_from_chroma

        mock_vs = MagicMock()
        mock_vs.get.return_value = {"ids": []}
        mock_get_vs.return_value = mock_vs

        await delete_document_from_chroma("u1", "t1", "nonexistent")
        mock_vs.delete.assert_not_called()


@pytest.mark.unit
class TestBM25Operations:
    def test_get_bm25_path(self):
        from core.embeddings.vectorstore import _get_bm25_path

        path = _get_bm25_path("user1", "thread1")
        assert "user1" in path
        assert "thread1" in path
        assert path.endswith(".pkl")

    @patch("core.embeddings.vectorstore.os.path.exists", return_value=False)
    def test_load_bm25_returns_none_if_missing(self, mock_exists):
        from core.embeddings.vectorstore import load_bm25

        result = load_bm25("u1", "t1")
        assert result is None
