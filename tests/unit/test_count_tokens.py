"""
Unit tests for core.utils.count_tokens — token counting utility.
"""

import pytest


@pytest.mark.unit
class TestCountTokens:
    def test_empty_string(self):
        from core.utils.count_tokens import count_tokens

        result = count_tokens("")
        assert result == 0

    def test_single_word(self):
        from core.utils.count_tokens import count_tokens

        result = count_tokens("hello")
        assert result >= 1

    def test_sentence(self):
        from core.utils.count_tokens import count_tokens

        result = count_tokens("The quick brown fox jumps over the lazy dog.")
        assert result > 5

    def test_known_model_mapping(self):
        from core.utils.count_tokens import count_tokens

        # qwen3:14b maps to cl100k_base
        result = count_tokens("Hello world", gpu_model="qwen3:14b")
        assert result >= 1

    def test_unknown_model_fallback(self):
        from core.utils.count_tokens import count_tokens

        # Unknown model should fall back to o200k_base
        result = count_tokens("Hello world", gpu_model="unknown-model:7b")
        assert result >= 1

    def test_default_model(self):
        from core.utils.count_tokens import count_tokens

        # Default is gpt-oss:20b → o200k_base
        result = count_tokens("Test text")
        assert isinstance(result, int)

    def test_long_text(self):
        from core.utils.count_tokens import count_tokens

        text = "word " * 1000
        result = count_tokens(text)
        assert result > 100

    def test_special_characters(self):
        from core.utils.count_tokens import count_tokens

        result = count_tokens("Hello! @#$%^&*() 日本語テスト")
        assert result >= 1

    def test_newlines_and_whitespace(self):
        from core.utils.count_tokens import count_tokens

        result = count_tokens("Line 1\nLine 2\n\nLine 4")
        assert result >= 3

    def test_returns_int(self):
        from core.utils.count_tokens import count_tokens

        result = count_tokens("test")
        assert isinstance(result, int)
