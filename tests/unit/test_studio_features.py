"""
Unit tests for core.studio_features.word_cloud — text cleaning and word cloud generation.
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.unit
class TestCleanText:
    def test_lowercase(self):
        from core.studio_features.word_cloud import clean_text

        result = clean_text("HELLO WORLD")
        assert result == result.lower()

    def test_removes_special_chars(self):
        from core.studio_features.word_cloud import clean_text

        result = clean_text("hello@world#2024")
        assert "@" not in result
        assert "#" not in result

    def test_removes_unicode_escapes(self):
        from core.studio_features.word_cloud import clean_text

        result = clean_text("test \\u00e9 data")
        assert "\\u" not in result

    def test_collapses_whitespace(self):
        from core.studio_features.word_cloud import clean_text

        result = clean_text("hello    world     test")
        assert "  " not in result

    def test_removes_stopwords(self):
        from core.studio_features.word_cloud import clean_text

        result = clean_text("This is a test of the system")
        # Common stopwords should be removed
        words = result.split()
        assert "is" not in words
        assert "a" not in words
        assert "the" not in words

    def test_empty_string(self):
        from core.studio_features.word_cloud import clean_text

        result = clean_text("")
        assert result == ""


@pytest.mark.unit
class TestLimitWords:
    def test_under_limit(self):
        from core.studio_features.word_cloud import limit_words

        text = "one two three"
        result = limit_words(text, max_words=10)
        assert result == text

    def test_over_limit(self):
        from core.studio_features.word_cloud import limit_words

        text = " ".join(f"word{i}" for i in range(100))
        result = limit_words(text, max_words=10)
        assert len(result.split()) == 10

    def test_exact_limit(self):
        from core.studio_features.word_cloud import limit_words

        text = "a b c d e"
        result = limit_words(text, max_words=5)
        assert len(result.split()) == 5


@pytest.mark.unit
class TestInsightsFetchDocumentContent:
    def test_single_doc_short_text(self):
        from core.studio_features.insights import fetch_document_content
        from core.models.document import Document

        doc = Document(
            id="d1",
            type="pdf",
            file_name="test.pdf",
            title="Test",
            full_text="Short text content",
        )
        result = fetch_document_content(doc)
        assert "Short text content" in result

    def test_single_doc_with_summary_fallback(self):
        from core.studio_features.insights import fetch_document_content
        from core.models.document import Document

        long_text = " ".join(["word"] * 10000)
        doc = Document(
            id="d1",
            type="pdf",
            file_name="test.pdf",
            title="Test",
            full_text=long_text,
            summary="Summary text",
        )
        result = fetch_document_content(doc)
        assert "Summary text" in result

    def test_word_count(self):
        from core.studio_features.insights import word_count

        assert word_count("one two three") == 3
        assert word_count("") == 0
        assert word_count("single") == 1
