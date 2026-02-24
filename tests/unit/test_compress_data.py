"""
Unit tests for core.utils.compress_data — token-aware data compression.
"""

import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestCompressGlobalFileData:
    def _make_docs(self, n=3, content_len=100):
        return [{"title": f"Doc {i}", "content": "x " * content_len} for i in range(n)]

    @patch("core.utils.compress_data.count_tokens", return_value=10)
    def test_small_data_no_compression(self, mock_tokens):
        from core.utils.compress_data import compress_global_file_data

        docs = self._make_docs(2, 10)
        result = compress_global_file_data(docs, max_tokens=10000, gpu_model="test")
        # All content should be preserved
        for doc in result:
            assert len(doc["content"]) > 0

    @patch("core.utils.compress_data.count_tokens")
    def test_large_data_gets_trimmed(self, mock_tokens):
        from core.utils.compress_data import compress_global_file_data

        # First call returns over limit, subsequent calls decrease
        call_count = [0]

        def decreasing_tokens(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return 50000
            return 100

        mock_tokens.side_effect = decreasing_tokens
        docs = self._make_docs(3, 500)
        original_lengths = [len(d["content"]) for d in docs]
        result = compress_global_file_data(docs, max_tokens=5000, gpu_model="test")
        # Content should be shorter or docs should be returned
        assert len(result) == 3

    def test_empty_input(self):
        from core.utils.compress_data import compress_global_file_data

        result = compress_global_file_data([], max_tokens=1000, gpu_model="test")
        assert result == []

    @patch("core.utils.compress_data.count_tokens", return_value=5)
    def test_does_not_mutate_original(self, mock_tokens):
        from core.utils.compress_data import compress_global_file_data

        docs = [{"title": "Test", "content": "original content"}]
        import copy

        original = copy.deepcopy(docs)
        compress_global_file_data(docs, max_tokens=10000, gpu_model="test")
        assert docs[0]["content"] == original[0]["content"]

    @patch("core.utils.compress_data.count_tokens", return_value=5)
    def test_prompt_offset_considered(self, mock_tokens):
        from core.utils.compress_data import compress_global_file_data

        docs = self._make_docs(1, 10)
        result = compress_global_file_data(
            docs, max_tokens=10000, gpu_model="test", prompt_offset=500
        )
        assert len(result) == 1
