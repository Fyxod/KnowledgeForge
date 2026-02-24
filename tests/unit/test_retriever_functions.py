"""
Unit tests for core.embeddings.retriever — rerank_chunks, get_user_retriever,
hybrid_retrieve, get_thread_documents_retriever.
"""

import math
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def _make_chunks(n=5, doc_id="d1"):
    """Create sample chunks for testing."""
    return [
        {
            "page_content": f"Content for chunk {i}",
            "metadata": {
                "document_id": doc_id,
                "page_no": i,
                "chunk_index": 0,
                "title": "Doc",
                "file_name": "doc.pdf",
            },
        }
        for i in range(n)
    ]


@pytest.mark.unit
class TestRerankChunks:
    @patch("core.embeddings.retriever.get_cross_encoder")
    def test_rerank_returns_sorted(self, mock_ce):
        from core.embeddings.retriever import rerank_chunks

        encoder = MagicMock()
        # Assign decreasing relevance scores
        encoder.predict.return_value = [0.9, 0.1, 0.5]
        mock_ce.return_value = encoder

        chunks = _make_chunks(3)
        result = rerank_chunks("test query", chunks, top_k=3)

        assert len(result) == 3
        # Highest relevance should come first
        assert result[0]["relevance_score"] == 0.9

    @patch("core.embeddings.retriever.get_cross_encoder")
    def test_rerank_top_k_limits(self, mock_ce):
        from core.embeddings.retriever import rerank_chunks

        encoder = MagicMock()
        encoder.predict.return_value = [0.5, 0.4, 0.3, 0.2, 0.1]
        mock_ce.return_value = encoder

        chunks = _make_chunks(5)
        result = rerank_chunks("query", chunks, top_k=2)

        assert len(result) == 2

    @patch("core.embeddings.retriever.get_cross_encoder")
    def test_rerank_diversity(self, mock_ce):
        from core.embeddings.retriever import rerank_chunks

        encoder = MagicMock()
        # Two identical chunks and one different
        encoder.predict.return_value = [0.9, 0.85, 0.8]
        mock_ce.return_value = encoder

        chunks = [
            {
                "page_content": "identical text",
                "metadata": {"document_id": "d1", "page_no": 1, "chunk_index": 0},
            },
            {
                "page_content": "identical text",
                "metadata": {"document_id": "d1", "page_no": 2, "chunk_index": 0},
            },
            {
                "page_content": "different content entirely",
                "metadata": {"document_id": "d2", "page_no": 1, "chunk_index": 0},
            },
        ]
        # diversity_lambda=0.5 penalizes similar chunks
        result = rerank_chunks("query", chunks, top_k=3, diversity_lambda=0.5)
        assert len(result) == 3

    def test_rerank_empty_chunks(self):
        from core.embeddings.retriever import rerank_chunks

        result = rerank_chunks("query", [], top_k=5)
        assert result == []

    @patch("core.embeddings.retriever.get_cross_encoder")
    def test_rerank_cross_encoder_failure(self, mock_ce):
        from core.embeddings.retriever import rerank_chunks

        mock_ce.side_effect = Exception("Model load failed")

        chunks = _make_chunks(3)
        result = rerank_chunks("query", chunks, top_k=3)

        # Should fallback to original order with default scores
        assert len(result) == 3
        # Check that relevance_score is set as fallback
        for chunk in result:
            assert "relevance_score" in chunk


@pytest.mark.unit
class TestGetUserRetriever:
    @patch("core.embeddings.retriever.get_vectorstore")
    def test_returns_retriever(self, mock_vs_fn):
        from core.embeddings.retriever import get_user_retriever

        mock_vs = MagicMock()
        mock_retriever = MagicMock()
        mock_vs.as_retriever.return_value = mock_retriever
        mock_vs_fn.return_value = mock_vs

        retriever = get_user_retriever("u1", "t1", k=5)

        assert retriever == mock_retriever
        mock_vs.as_retriever.assert_called_once()

    @patch("core.embeddings.retriever.get_vectorstore")
    def test_with_document_id_filter(self, mock_vs_fn):
        from core.embeddings.retriever import get_user_retriever

        mock_vs = MagicMock()
        mock_vs.as_retriever.return_value = MagicMock()
        mock_vs_fn.return_value = mock_vs

        get_user_retriever("u1", "t1", document_id="doc1", k=10)

        call_kwargs = mock_vs.as_retriever.call_args[1]
        filter_conds = call_kwargs["search_kwargs"]["filter"]["$and"]
        doc_filter = [c for c in filter_conds if "document_id" in c]
        assert len(doc_filter) == 1


@pytest.mark.unit
class TestHybridRetrieve:
    @pytest.mark.asyncio
    @patch("core.embeddings.retriever.search_bm25")
    @patch("core.embeddings.retriever.get_user_retriever")
    async def test_hybrid_combines_results(self, mock_retriever_fn, mock_bm25):
        from core.embeddings.retriever import hybrid_retrieve

        # Mock vector retriever
        mock_retriever = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.model_dump.return_value = {
            "page_content": "vector result",
            "metadata": {"document_id": "d1", "page_no": 1, "chunk_index": 0},
        }
        mock_retriever.ainvoke.return_value = [mock_doc]
        mock_retriever_fn.return_value = mock_retriever

        # Mock BM25 results
        mock_bm25.return_value = [
            {
                "page_content": "bm25 result",
                "metadata": {"document_id": "d2", "page_no": 1, "chunk_index": 0},
                "bm25_score": 5.0,
            }
        ]

        result = await hybrid_retrieve("u1", "t1", "test query")

        assert len(result) >= 1

    @pytest.mark.asyncio
    @patch("core.embeddings.retriever.search_bm25")
    @patch("core.embeddings.retriever.get_user_retriever")
    async def test_hybrid_no_bm25_results(self, mock_retriever_fn, mock_bm25):
        from core.embeddings.retriever import hybrid_retrieve

        mock_retriever = AsyncMock()
        mock_doc = MagicMock()
        mock_doc.model_dump.return_value = {
            "page_content": "vector only",
            "metadata": {"document_id": "d1", "page_no": 1, "chunk_index": 0},
        }
        mock_retriever.ainvoke.return_value = [mock_doc]
        mock_retriever_fn.return_value = mock_retriever

        mock_bm25.return_value = []

        result = await hybrid_retrieve("u1", "t1", "query")

        # Should return vector results directly
        assert len(result) == 1
        assert result[0]["page_content"] == "vector only"


@pytest.mark.unit
class TestGetThreadDocumentsRetriever:
    @pytest.mark.asyncio
    @patch("core.embeddings.retriever.hybrid_retrieve", new_callable=AsyncMock)
    async def test_adaptive_k_few_documents(self, mock_hybrid):
        from core.embeddings.retriever import get_thread_documents_retriever

        # 2 unique documents
        mock_hybrid.return_value = [
            {
                "page_content": f"chunk{i}",
                "metadata": {
                    "document_id": f"d{i % 2}",
                    "page_no": i,
                    "chunk_index": 0,
                },
            }
            for i in range(10)
        ]

        result = await get_thread_documents_retriever("u1", "t1", query="test")

        assert len(result) > 0

    @pytest.mark.asyncio
    @patch("core.embeddings.retriever.hybrid_retrieve", new_callable=AsyncMock)
    async def test_empty_retrieval(self, mock_hybrid):
        from core.embeddings.retriever import get_thread_documents_retriever

        mock_hybrid.return_value = []

        result = await get_thread_documents_retriever("u1", "t1", query="test")

        assert result == []

    @pytest.mark.asyncio
    @patch("core.embeddings.retriever.hybrid_retrieve", new_callable=AsyncMock)
    async def test_many_documents_higher_k(self, mock_hybrid):
        from core.embeddings.retriever import get_thread_documents_retriever

        # 8 different documents
        mock_hybrid.return_value = [
            {
                "page_content": f"chunk{i}",
                "metadata": {"document_id": f"d{i}", "page_no": 1, "chunk_index": 0},
            }
            for i in range(8)
        ]

        result = await get_thread_documents_retriever("u1", "t1", query="test")

        assert len(result) > 0
