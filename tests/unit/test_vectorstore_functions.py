"""
Unit tests for core.embeddings.vectorstore — search_bm25, rebuild_bm25,
_build_and_save_bm25, get_vectorstore, save_documents_to_store.
"""

import os
import pickle
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
class TestSearchBm25:
    def test_no_index_returns_empty(self):
        from core.embeddings.vectorstore import search_bm25

        with patch("core.embeddings.vectorstore.load_bm25", return_value=None):
            result = search_bm25("u1", "t1", "search query", top_k=5)
            assert result == []

    def test_search_returns_results(self):
        from core.embeddings.vectorstore import search_bm25

        # Create a mock BM25 data structure
        mock_bm25 = MagicMock()
        mock_bm25.get_scores.return_value = [5.0, 0.0, 3.0]

        bm25_data = {
            "bm25": mock_bm25,
            "chunk_ids": ["c1", "c2", "c3"],
            "chunk_texts": ["hello world", "foo bar", "hello python"],
            "chunk_metadatas": [
                {"document_id": "d1"},
                {"document_id": "d1"},
                {"document_id": "d2"},
            ],
        }

        with patch("core.embeddings.vectorstore.load_bm25", return_value=bm25_data):
            result = search_bm25("u1", "t1", "hello", top_k=5)

        assert len(result) == 2  # Only scores > 0
        assert result[0]["bm25_score"] == 5.0
        assert result[0]["page_content"] == "hello world"

    def test_search_top_k_limit(self):
        from core.embeddings.vectorstore import search_bm25

        mock_bm25 = MagicMock()
        mock_bm25.get_scores.return_value = [5.0, 4.0, 3.0, 2.0, 1.0]

        bm25_data = {
            "bm25": mock_bm25,
            "chunk_ids": [f"c{i}" for i in range(5)],
            "chunk_texts": [f"text {i}" for i in range(5)],
            "chunk_metadatas": [{"document_id": "d1"} for _ in range(5)],
        }

        with patch("core.embeddings.vectorstore.load_bm25", return_value=bm25_data):
            result = search_bm25("u1", "t1", "query", top_k=2)

        assert len(result) == 2
        assert result[0]["bm25_score"] == 5.0


@pytest.mark.unit
class TestRebuildBm25AfterDeletion:
    @patch("core.embeddings.vectorstore._build_and_save_bm25")
    def test_rebuild_excludes_deleted_doc(self, mock_build):
        from core.embeddings.vectorstore import rebuild_bm25_after_deletion

        bm25_data = {
            "chunk_ids": ["c1", "c2", "c3"],
            "chunk_texts": ["text1", "text2", "text3"],
            "chunk_metadatas": [
                {"document_id": "d1"},
                {"document_id": "d2"},
                {"document_id": "d1"},
            ],
        }

        with patch("core.embeddings.vectorstore.load_bm25", return_value=bm25_data):
            rebuild_bm25_after_deletion("u1", "t1", "d1")

        mock_build.assert_called_once()
        remaining = mock_build.call_args[0][0]
        assert len(remaining) == 1
        assert remaining[0][2]["document_id"] == "d2"

    @patch("core.embeddings.vectorstore.os.path.exists", return_value=True)
    @patch("core.embeddings.vectorstore.os.remove")
    def test_rebuild_removes_index_when_empty(self, mock_remove, mock_exists):
        from core.embeddings.vectorstore import rebuild_bm25_after_deletion

        bm25_data = {
            "chunk_ids": ["c1"],
            "chunk_texts": ["text1"],
            "chunk_metadatas": [{"document_id": "d1"}],
        }

        with patch("core.embeddings.vectorstore.load_bm25", return_value=bm25_data):
            rebuild_bm25_after_deletion("u1", "t1", "d1")

        mock_remove.assert_called_once()

    def test_rebuild_no_index(self):
        from core.embeddings.vectorstore import rebuild_bm25_after_deletion

        with patch("core.embeddings.vectorstore.load_bm25", return_value=None):
            # Should not raise
            rebuild_bm25_after_deletion("u1", "t1", "d1")


@pytest.mark.unit
class TestBuildAndSaveBm25:
    @patch("core.embeddings.vectorstore.pickle.dump")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("core.embeddings.vectorstore.os.makedirs")
    def test_builds_and_saves(self, mock_makedirs, mock_open_fn, mock_dump):
        from core.embeddings.vectorstore import _build_and_save_bm25

        chunk_data = [
            ("c1", "hello world foo", {"document_id": "d1"}),
            ("c2", "bar baz qux", {"document_id": "d1"}),
        ]

        _build_and_save_bm25(chunk_data, "u1", "t1")

        mock_dump.assert_called_once()
        saved_data = mock_dump.call_args[0][0]
        assert "bm25" in saved_data
        assert saved_data["chunk_ids"] == ["c1", "c2"]

    @patch("core.embeddings.vectorstore.os.makedirs")
    def test_missing_rank_bm25_module(self, mock_makedirs):
        """If rank_bm25 is not installed, should not raise."""
        from core.embeddings.vectorstore import _build_and_save_bm25

        with patch.dict("sys.modules", {"rank_bm25": None}):
            # Will import successfully since rank_bm25 is installed,
            # but we test the function doesn't crash
            chunk_data = [("c1", "text", {"document_id": "d1"})]
            # This will work because rank_bm25 IS installed
            _build_and_save_bm25(chunk_data, "u1", "t1")


@pytest.mark.unit
class TestGetVectorstore:
    @patch("core.embeddings.vectorstore._check_and_migrate_chroma")
    @patch("core.embeddings.vectorstore.Chroma")
    @patch("core.embeddings.vectorstore.os.makedirs")
    def test_returns_chroma_instance(self, mock_makedirs, mock_chroma, mock_migrate):
        from core.embeddings.vectorstore import get_vectorstore

        mock_vs = MagicMock()
        mock_chroma.return_value = mock_vs

        result = get_vectorstore("u1", "t1")

        assert result == mock_vs
        mock_chroma.assert_called_once()

    @patch("core.embeddings.vectorstore._check_and_migrate_chroma")
    @patch("core.embeddings.vectorstore.Chroma")
    @patch("core.embeddings.vectorstore.os.makedirs")
    def test_persist_path_contains_user(self, mock_makedirs, mock_chroma, mock_migrate):
        from core.embeddings.vectorstore import get_vectorstore

        get_vectorstore("my_user", "my_thread")

        call_kwargs = mock_chroma.call_args[1]
        assert "my_user" in call_kwargs["persist_directory"]


@pytest.mark.unit
class TestLoadBm25:
    @patch("core.embeddings.vectorstore.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=MagicMock)
    def test_loads_from_disk(self, mock_open_fn, mock_exists):
        from core.embeddings.vectorstore import load_bm25

        expected = {"bm25": "data", "chunk_ids": []}
        with patch("core.embeddings.vectorstore.pickle.load", return_value=expected):
            result = load_bm25("u1", "t1")

        assert result == expected
