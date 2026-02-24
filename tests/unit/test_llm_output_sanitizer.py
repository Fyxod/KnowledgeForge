"""
Unit tests for core.utils.llm_output_sanitizer — JSON cleaning, parsing, and normalization.
"""

import json

import pytest
from pydantic import BaseModel


class SampleSchema(BaseModel):
    answer: str
    score: int = 0


class NestedSchema(BaseModel):
    name: str
    items: list = []


@pytest.mark.unit
class TestSanitizeLlmJson:
    def test_clean_json_passthrough(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '{"answer": "hello", "score": 5}'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert parsed["answer"] == "hello"

    def test_strips_code_fences(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '```json\n{"answer": "hello"}\n```'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert parsed["answer"] == "hello"

    def test_strips_json_uppercase_fence(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '```JSON\n{"answer": "hello"}\n```'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert parsed["answer"] == "hello"

    def test_removes_unicode_whitespace(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '{"answer":\u00a0"hello"}'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert parsed["answer"] == "hello"

    def test_removes_zero_width_chars(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '{"answer": "hel\u200blo"}'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert "hello" in parsed["answer"]

    def test_empty_string(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        result = sanitize_llm_json("")
        assert result == ""

    def test_none_passthrough(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        result = sanitize_llm_json(None)
        assert result is None

    def test_extracts_json_from_prefix_text(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = 'Here is the response:\n{"answer": "hello"}\nDone.'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert parsed["answer"] == "hello"

    def test_handles_newlines_in_strings(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '{"answer": "line1\nline2"}'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert "line1" in parsed["answer"]

    def test_array_extraction(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = 'Prefix [{"a": 1}, {"a": 2}] suffix'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2


@pytest.mark.unit
class TestParseLlmJson:
    def test_valid_json(self):
        from core.utils.llm_output_sanitizer import parse_llm_json

        raw = '{"answer": "hello", "score": 5}'
        result = parse_llm_json(raw, SampleSchema)
        assert result.answer == "hello"
        assert result.score == 5

    def test_json_with_code_fence(self):
        from core.utils.llm_output_sanitizer import parse_llm_json

        raw = '```json\n{"answer": "test", "score": 10}\n```'
        result = parse_llm_json(raw, SampleSchema)
        assert result.answer == "test"

    def test_missing_optional_field_uses_default(self):
        from core.utils.llm_output_sanitizer import parse_llm_json

        raw = '{"answer": "hello"}'
        result = parse_llm_json(raw, SampleSchema)
        assert result.score == 0

    def test_invalid_json_raises(self):
        from core.utils.llm_output_sanitizer import parse_llm_json

        raw = "This is not JSON at all"
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_llm_json(raw, SampleSchema)

    def test_nested_schema(self):
        from core.utils.llm_output_sanitizer import parse_llm_json

        raw = '{"name": "test", "items": [1, 2, 3]}'
        result = parse_llm_json(raw, NestedSchema)
        assert result.name == "test"
        assert len(result.items) == 3


@pytest.mark.unit
class TestNormalizeAnswerContent:
    def test_escaped_newlines(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content("line1\\nline2")
        assert result == "line1\nline2"

    def test_escaped_tabs(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content("col1\\tcol2")
        assert result == "col1\tcol2"

    def test_escaped_quotes(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content('He said \\"hello\\"')
        assert result == 'He said "hello"'

    def test_escaped_slashes(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content("path\\/to\\/file")
        assert result == "path/to/file"

    def test_excessive_newlines_collapsed(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content("a\n\n\n\n\nb")
        assert result == "a\n\nb"

    def test_empty_string(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content("")
        assert result == ""

    def test_none_returns_none(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content(None)
        assert result is None

    def test_double_backslashes_preserved(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        result = normalize_answer_content("C:\\\\Users\\\\test")
        assert "\\" in result
