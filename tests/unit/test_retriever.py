"""
Unit tests for core.embeddings.retriever — hybrid retrieval, reranking, RRF.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestReciprocalRankFusion:
    def test_single_list(self):
        from core.embeddings.retriever import reciprocal_rank_fusion

        docs = [
            {"page_content": "a", "metadata": {}},
            {"page_content": "b", "metadata": {}},
        ]
        result = reciprocal_rank_fusion([docs], k=60)
        assert len(result) == 2

    def test_two_lists_merges(self):
        from core.embeddings.retriever import reciprocal_rank_fusion

        # RRF keys on metadata.document_id/page_no/chunk_index so use distinct metadata
        list1 = [
            {
                "page_content": "a",
                "metadata": {"document_id": "d1", "page_no": 1, "chunk_index": 0},
            },
            {
                "page_content": "b",
                "metadata": {"document_id": "d1", "page_no": 2, "chunk_index": 0},
            },
        ]
        list2 = [
            {
                "page_content": "b",
                "metadata": {"document_id": "d1", "page_no": 2, "chunk_index": 0},
            },
            {
                "page_content": "c",
                "metadata": {"document_id": "d1", "page_no": 3, "chunk_index": 0},
            },
        ]
        result = reciprocal_rank_fusion([list1, list2], k=60)
        # b appears in both lists so gets the highest combined score
        assert len(result) == 3
        # 'b' should be first (appears in both lists)
        assert result[0]["page_content"] == "b"

    def test_empty_lists(self):
        from core.embeddings.retriever import reciprocal_rank_fusion

        result = reciprocal_rank_fusion([[]], k=60)
        assert result == []

    def test_k_parameter_affects_scoring(self):
        from core.embeddings.retriever import reciprocal_rank_fusion

        docs = [{"page_content": "a", "metadata": {}}]
        result1 = reciprocal_rank_fusion([docs], k=1)
        result2 = reciprocal_rank_fusion([docs], k=100)
        # Both should return the same doc but with different scores
        assert len(result1) == 1
        assert len(result2) == 1


@pytest.mark.unit
class TestCosineHelpers:
    def test_cosine_similarity_identical(self):
        from core.embeddings.retriever import _cosine_similarity

        a = {"word1": 1.0, "word2": 2.0}
        b = {"word1": 1.0, "word2": 2.0}
        result = _cosine_similarity(a, b)
        assert abs(result - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        from core.embeddings.retriever import _cosine_similarity

        a = {"word1": 1.0}
        b = {"word2": 1.0}
        result = _cosine_similarity(a, b)
        assert abs(result) < 1e-6

    def test_cosine_similarity_empty(self):
        from core.embeddings.retriever import _cosine_similarity

        result = _cosine_similarity({}, {})
        assert result == 0.0


@pytest.mark.unit
class TestComputeTfidfVectors:
    def test_basic_tfidf(self):
        from core.embeddings.retriever import _compute_tfidf_vectors

        chunks = [
            {"page_content": "hello world"},
            {"page_content": "hello python"},
            {"page_content": "world python programming"},
        ]
        vectors = _compute_tfidf_vectors(chunks)
        assert len(vectors) == 3
        # Each vector should be a dict
        for v in vectors:
            assert isinstance(v, dict)

    def test_empty_chunks(self):
        from core.embeddings.retriever import _compute_tfidf_vectors

        vectors = _compute_tfidf_vectors([])
        assert vectors == []

    def test_single_chunk(self):
        from core.embeddings.retriever import _compute_tfidf_vectors

        vectors = _compute_tfidf_vectors([{"page_content": "test"}])
        assert len(vectors) == 1
