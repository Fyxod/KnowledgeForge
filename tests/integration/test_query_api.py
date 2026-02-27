"""
Integration tests for /query API endpoint.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent.state import AgentState


@pytest.mark.integration
class TestQueryEndpoint:
    @pytest.mark.asyncio
    async def test_query_no_auth(self, async_client, patched_db):
        response = await async_client.post(
            "/query/",
            json={"thread_id": "t1", "question": "Hello?"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_query_user_not_found(self, async_client, patched_db, auth_headers):
        response = await async_client.post(
            "/query/",
            json={"thread_id": "t1", "question": "Hello?"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_query_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/query/",
            json={"thread_id": "nonexistent", "question": "Hello?"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    @patch("app.routes.query.combination_node", new_callable=AsyncMock)
    @patch("app.routes.query.Agent")
    @patch("app.routes.query.decomposition_node", new_callable=AsyncMock)
    @patch("app.routes.query.search_tool", new_callable=AsyncMock)
    @patch("app.routes.query.SQLiteManager")
    @patch("app.routes.query.is_extra_done", return_value=False)
    async def test_query_no_decomposition(
        self,
        mock_extra_done,
        mock_sqlite,
        mock_search,
        mock_decomp,
        mock_agent,
        mock_comb,
        async_client,
        populated_db,
        auth_headers,
    ):
        """Single query (no decomposition) round-trip."""
        from core.llm.outputs import DecompositionLLMOutput

        mock_sqlite.has_spreadsheet_data.return_value = False
        mock_decomp.return_value = DecompositionLLMOutput(
            requires_decomposition=False,
            resolved_query="What is AI?",
            sub_queries=[],
        )
        mock_search.return_value = {"answer": "", "results": []}

        # Build a realistic agent return value
        mock_state = {
            "user_id": "user_test_123",
            "thread_id": "thread_001",
            "query": "What is AI?",
            "resolved_query": "What is AI?",
            "original_query": "What is AI?",
            "messages": [],
            "chunks": [],
            "web_search": False,
            "web_search_queries": [],
            "web_search_results": [],
            "document_id": None,
            "after_summary": "generate",
            "summary": None,
            "answer": "AI is artificial intelligence.",
            "chunks_used": [],
            "confidence_score": "high",
            "attempts": 0,
            "web_search_attempts": 0,
            "sql_query": None,
            "sql_result": None,
            "sql_attempts": 0,
            "has_spreadsheet_data": False,
            "spreadsheet_schema": None,
            "action": "answer",
            "next": None,
            "llm": {"model": "test", "port": 11434},
            "mode": "External",
            "initial_search_answer": "",
            "initial_search_results": [],
            "use_self_knowledge": False,
            "thread_instructions": [],
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_state)

        response = await async_client.post(
            "/query/",
            json={
                "thread_id": "thread_001",
                "question": "What is AI?",
                "mode": "External",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "AI is artificial intelligence."
        assert data["question"] == "What is AI?"
        assert "confidence_score" in data
        assert "confidence_score" in data

    @pytest.mark.asyncio
    async def test_query_missing_question(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/query/",
            json={"thread_id": "thread_001"},
            headers=auth_headers,
        )
        assert response.status_code == 422
