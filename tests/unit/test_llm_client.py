"""
Unit tests for core.llm.client — LLM invocation with retry/fallback logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel


class MockSchema(BaseModel):
    answer: str
    score: int = 0


@pytest.mark.unit
class TestGetCachedLlm:
    @patch("core.llm.client.MyServerLLM")
    def test_caches_same_key(self, MockLLM):
        from core.llm.client import _get_cached_llm, _llm_cache

        _llm_cache.clear()
        MockLLM.return_value = MagicMock()
        llm1 = _get_cached_llm("model1", 11434)
        llm2 = _get_cached_llm("model1", 11434)
        assert llm1 is llm2
        assert MockLLM.call_count == 1

    @patch("core.llm.client.MyServerLLM")
    def test_different_keys_create_new(self, MockLLM):
        from core.llm.client import _get_cached_llm, _llm_cache

        _llm_cache.clear()
        # side_effect returns a new MagicMock each call
        MockLLM.side_effect = lambda **kwargs: MagicMock(**kwargs)
        llm1 = _get_cached_llm("model1", 11434)
        llm2 = _get_cached_llm("model2", 11434)
        assert llm1 is not llm2
        _llm_cache.clear()


@pytest.mark.unit
class TestTryParse:
    def test_valid_json(self):
        from core.llm.client import _try_parse
        from langchain_core.output_parsers import PydanticOutputParser

        parser = PydanticOutputParser(pydantic_object=MockSchema)
        result = _try_parse('{"answer": "test", "score": 5}', parser, MockSchema)
        assert result.answer == "test"

    def test_json_with_fences(self):
        from core.llm.client import _try_parse
        from langchain_core.output_parsers import PydanticOutputParser

        parser = PydanticOutputParser(pydantic_object=MockSchema)
        raw = '```json\n{"answer": "fenced", "score": 1}\n```'
        result = _try_parse(raw, parser, MockSchema)
        assert result.answer == "fenced"


@pytest.mark.unit
class TestNextApiKey:
    @pytest.mark.asyncio
    async def test_cycles_keys(self):
        from core.llm.client import _next_api_key

        keys = set()
        for _ in range(12):
            key = await _next_api_key()
            keys.add(key)
        # Should cycle through 6 unique keys
        assert len(keys) == 6
