"""
Unit tests for core.llm.client — invoke_llm with Gemini/OpenAI fallback.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pydantic import BaseModel


class TestSchema(BaseModel):
    answer: str
    action: str = "Answer"


@pytest.mark.unit
class TestInvokeLlm:
    @pytest.mark.asyncio
    @patch(
        "core.llm.client.SWITCHES",
        {"REMOTE_GPU": False, "FALLBACK_TO_GEMINI": True, "FALLBACK_TO_OPENAI": False},
    )
    @patch("core.llm.client._next_api_key", new_callable=AsyncMock)
    @patch("core.llm.client.genai")
    async def test_gemini_success(self, mock_genai, mock_key):
        from core.llm.client import invoke_llm

        mock_key.return_value = "test-api-key"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"answer": "Gemini response", "action": "Answer"}'
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        # Mock asyncio.to_thread to call synchronously
        with patch(
            "core.llm.client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_thread:
            mock_thread.return_value = mock_response
            with patch(
                "core.llm.client.asyncio.wait_for", new_callable=AsyncMock
            ) as mock_wait:
                mock_wait.return_value = mock_response

                result = await invoke_llm(
                    gpu_model="test",
                    response_schema=TestSchema,
                    contents="test prompt",
                    port=11434,
                )

        assert result.answer == "Gemini response"

    @pytest.mark.asyncio
    @patch(
        "core.llm.client.SWITCHES",
        {"REMOTE_GPU": False, "FALLBACK_TO_GEMINI": False, "FALLBACK_TO_OPENAI": True},
    )
    @patch("core.llm.client.openai_client")
    async def test_openai_success(self, mock_openai):
        from core.llm.client import invoke_llm

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"answer": "OpenAI response", "action": "Answer"}'
        )
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await invoke_llm(
            gpu_model="test",
            response_schema=TestSchema,
            contents="test prompt",
            port=11434,
        )

        assert result.answer == "OpenAI response"

    @pytest.mark.asyncio
    @patch("core.llm.client.asyncio.sleep", new_callable=AsyncMock)
    @patch(
        "core.llm.client.SWITCHES",
        {"REMOTE_GPU": False, "FALLBACK_TO_GEMINI": False, "FALLBACK_TO_OPENAI": False},
    )
    async def test_all_fallbacks_disabled_raises(self, mock_sleep):
        from core.llm.client import invoke_llm

        with pytest.raises(RuntimeError, match="All .* attempts failed"):
            await invoke_llm(
                gpu_model="test",
                response_schema=TestSchema,
                contents="test prompt",
                port=11434,
            )

    @pytest.mark.asyncio
    @patch("core.llm.client.asyncio.sleep", new_callable=AsyncMock)
    @patch(
        "core.llm.client.SWITCHES",
        {"REMOTE_GPU": False, "FALLBACK_TO_GEMINI": False, "FALLBACK_TO_OPENAI": True},
    )
    @patch("core.llm.client.openai_client")
    async def test_openai_all_retries_fail(self, mock_openai, mock_sleep):
        from core.llm.client import invoke_llm

        mock_openai.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        with pytest.raises(RuntimeError, match="All .* attempts failed"):
            await invoke_llm(
                gpu_model="test",
                response_schema=TestSchema,
                contents="test prompt",
            )
