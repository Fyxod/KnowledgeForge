"""
Extended unit tests for core.utils.count_tokens — covers ValueError fallback.
Extended tests for core.utils.compress_data — covers the trimming loop.
Extended tests for core.utils.generation_status — covers more status reader paths.
Extended tests for core.utils.llm_output_sanitizer — covers more edge cases.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ═══════════════════════════════════════════════════════════════════════
# count_tokens — ValueError fallback
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCountTokensValueError:
    def test_invalid_encoding_falls_back(self):
        """When tiktoken.get_encoding raises ValueError, falls back to cl100k_base."""
        from core.utils.count_tokens import count_tokens

        # Patch the map to return an invalid encoding name
        with patch(
            "core.utils.count_tokens.map", {"bad_model": "NONEXISTENT_ENCODING"}
        ):
            result = count_tokens("hello world", gpu_model="bad_model")
        assert isinstance(result, int)
        assert result > 0


# ═══════════════════════════════════════════════════════════════════════
# compress_data — trimming loop
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCompressDataTrimming:
    def test_already_within_limit(self):
        from core.utils.compress_data import compress_global_file_data

        docs = [{"title": "T", "content": "Short"}]
        result = compress_global_file_data(
            docs, max_tokens=50000, gpu_model="gpt-oss:20b"
        )
        assert result[0]["content"] == "Short"

    def test_trims_long_content(self):
        from core.utils.compress_data import compress_global_file_data

        # Content far exceeding the token limit forces trimming
        big_content = "word " * 200_000  # ~200k tokens
        docs = [{"title": "T", "content": big_content}]
        result = compress_global_file_data(
            docs, max_tokens=100, gpu_model="gpt-oss:20b", prompt_offset=0
        )
        # The content should be significantly shorter than the original
        assert len(result[0]["content"]) < len(big_content)

    def test_does_not_mutate_original(self):
        from core.utils.compress_data import compress_global_file_data

        original = [{"title": "T", "content": "hello " * 100_000}]
        original_content = original[0]["content"]
        compress_global_file_data(original, max_tokens=50, gpu_model="gpt-oss:20b")
        # Original should not be mutated (defensive copy)
        assert original[0]["content"] == original_content

    def test_multiple_docs_trimmed(self):
        from core.utils.compress_data import compress_global_file_data

        docs = [
            {"title": "A", "content": "word " * 100_000},
            {"title": "B", "content": "word " * 100_000},
        ]
        result = compress_global_file_data(
            docs, max_tokens=200, gpu_model="gpt-oss:20b", prompt_offset=0
        )
        for doc in result:
            assert len(doc["content"]) < 100_000 * 5


# ═══════════════════════════════════════════════════════════════════════
# generation_status — extended reader tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestGenerationStatusExtended:
    @pytest.mark.asyncio
    async def test_read_empty_file(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        p = tmp_path / "status.json"
        p.write_text("")
        result = await read_generation_status(str(p))
        assert result["state"] == "failed"
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_corrupted_json(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        p = tmp_path / "status.json"
        p.write_text("{not valid json")
        result = await read_generation_status(str(p))
        assert result["state"] == "failed"
        assert "corrupted" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_non_dict_json(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        p = tmp_path / "status.json"
        p.write_text('"just a string"')
        result = await read_generation_status(str(p))
        assert result["state"] == "failed"
        assert "unexpected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_failed_status(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        p = tmp_path / "status.json"
        p.write_text(json.dumps({"_status": "failed", "error": "boom"}))
        result = await read_generation_status(str(p))
        assert result["state"] == "failed"
        assert result["error"] == "boom"

    @pytest.mark.asyncio
    async def test_read_completed_status(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        p = tmp_path / "status.json"
        p.write_text(json.dumps({"key": "value", "data": [1, 2]}))
        result = await read_generation_status(str(p))
        assert result["state"] == "completed"
        assert result["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_read_stale_pending(self, tmp_path):
        from core.utils.generation_status import read_generation_status
        from datetime import datetime, timezone, timedelta

        stale_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        p = tmp_path / "status.json"
        p.write_text(json.dumps({"_status": "pending", "started_at": stale_time}))
        result = await read_generation_status(str(p))
        assert result["state"] == "failed"
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_write_pending(self, tmp_path):
        from core.utils.generation_status import write_pending_status

        p = tmp_path / "sub" / "status.json"
        await write_pending_status(str(p))
        content = json.loads(p.read_text())
        assert content["_status"] == "pending"

    @pytest.mark.asyncio
    async def test_write_failed(self, tmp_path):
        from core.utils.generation_status import write_failed_status

        p = tmp_path / "status.json"
        p.write_text("{}")  # create file first
        await write_failed_status(str(p), "test error")
        content = json.loads(p.read_text())
        assert content["_status"] == "failed"
        assert content["error"] == "test error"

    @pytest.mark.asyncio
    async def test_write_result(self, tmp_path):
        from core.utils.generation_status import write_result

        p = tmp_path / "status.json"
        await write_result(str(p), {"answer": 42})
        content = json.loads(p.read_text())
        assert content["answer"] == 42


# ═══════════════════════════════════════════════════════════════════════
# llm_output_sanitizer — extended edge cases
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestSanitizerExtended:
    def test_unicode_whitespace_replaced(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '{"key":\u00a0"value"}'
        result = sanitize_llm_json(raw)
        # Non-breaking space should be replaced with regular space
        assert "\u00a0" not in result

    def test_zero_width_chars_removed(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '{"key":\u200b"value"}'
        result = sanitize_llm_json(raw)
        assert "\u200b" not in result

    def test_code_fence_stripped(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = '```json\n{"key": "value"}\n```'
        result = sanitize_llm_json(raw)
        assert "```" not in result
        assert '"key"' in result

    def test_preamble_extracted(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        raw = 'Here is the JSON:\n{"key": "value"}\nDone!'
        result = sanitize_llm_json(raw)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_empty_string(self):
        from core.utils.llm_output_sanitizer import sanitize_llm_json

        assert sanitize_llm_json("") == ""
        assert sanitize_llm_json("   ") == "   "

    def test_normalize_answer_double_escaped(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        text = 'Hello\\nWorld\\tTab\\"quote'
        result = normalize_answer_content(text)
        assert "\n" in result
        assert "\t" in result
        assert '"' in result

    def test_normalize_answer_excessive_newlines(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        text = "a\n\n\n\n\nb"
        result = normalize_answer_content(text)
        assert "\n\n\n" not in result  # max 2 consecutive newlines

    def test_normalize_answer_empty(self):
        from core.utils.llm_output_sanitizer import normalize_answer_content

        assert normalize_answer_content("") == ""
        assert normalize_answer_content(None) is None

    def test_parse_llm_json_success(self):
        from core.utils.llm_output_sanitizer import parse_llm_json
        from pydantic import BaseModel

        class Simple(BaseModel):
            name: str

        result = parse_llm_json('{"name": "test"}', Simple)
        assert result.name == "test"

    def test_parse_llm_json_with_repair(self):
        from core.utils.llm_output_sanitizer import parse_llm_json
        from pydantic import BaseModel

        class Simple(BaseModel):
            name: str

        # Trailing comma — json_repair can fix this
        result = parse_llm_json('{"name": "test",}', Simple)
        assert result.name == "test"

    def test_parse_llm_json_failure(self):
        from core.utils.llm_output_sanitizer import parse_llm_json
        from pydantic import BaseModel

        class Simple(BaseModel):
            name: str

        with pytest.raises(ValueError):
            parse_llm_json("totally not json at all", Simple)

    def test_escape_control_chars_in_strings(self):
        from core.utils.llm_output_sanitizer import _escape_control_chars_in_strings

        # Newline inside a string should be escaped
        raw = '{"key": "line1\nline2"}'
        result = _escape_control_chars_in_strings(raw)
        parsed = json.loads(result)
        assert "line1" in parsed["key"]
