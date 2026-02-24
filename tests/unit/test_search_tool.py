"""
Unit tests for agent.tools.search — Tavily web search integration.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
class TestSearchTavily:
    @pytest.mark.asyncio
    @patch("agent.tools.search.client")
    async def test_successful_search(self, mock_client):
        from agent.tools.search import search_tavily

        mock_client.search.return_value = {
            "answer": "Test answer",
            "results": [{"title": "Result", "url": "https://example.com"}],
        }
        result = await search_tavily("test query")
        assert result["answer"] == "Test answer"
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    @patch("agent.tools.search.client")
    async def test_returns_empty_on_max_retries(self, mock_client):
        from agent.tools.search import search_tavily

        mock_client.search.side_effect = Exception("API error")
        result = await search_tavily("failing query")
        assert result == {}

    @pytest.mark.asyncio
    @patch("agent.tools.search.client")
    async def test_retries_on_failure(self, mock_client):
        from agent.tools.search import search_tavily

        # Fail twice, succeed on third
        mock_client.search.side_effect = [
            Exception("err"),
            Exception("err"),
            {"answer": "ok", "results": []},
        ]
        result = await search_tavily("query")
        assert result["answer"] == "ok"
        assert mock_client.search.call_count == 3

    @pytest.mark.asyncio
    @patch("agent.tools.search.client")
    async def test_custom_max_results(self, mock_client):
        from agent.tools.search import search_tavily

        mock_client.search.return_value = {"answer": "ok", "results": []}
        await search_tavily("query", max_results=10)
        call_kwargs = mock_client.search.call_args
        assert (
            call_kwargs.kwargs.get("max_results") == 10
            or call_kwargs[1].get("max_results") == 10
        )
