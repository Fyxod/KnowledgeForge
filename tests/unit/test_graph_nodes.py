"""
Unit tests for agent.graph_nodes — routing logic and node functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent.state import AgentState
from core.constants import (
    ANSWER,
    WEB_SEARCH,
    FAILURE,
    DOCUMENT_SUMMARIZER,
    GLOBAL_SUMMARIZER,
    GENERATE,
    SQL_QUERY,
    MAX_WEB_SEARCH,
    MAX_SQL_RETRIES,
)


def _make_state(**overrides):
    defaults = {
        "user_id": "u1",
        "thread_id": "t1",
        "query": "test query",
        "resolved_query": "test query",
        "original_query": "test query",
        "messages": [],
        "mode": "External",
        "llm": {"model": "test", "port": 11434},
    }
    defaults.update(overrides)
    return AgentState(**defaults)


@pytest.mark.unit
class TestMainRouter:
    def test_routes_to_answer(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=ANSWER)
        assert main_router(state) == ANSWER

    def test_routes_to_web_search(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=WEB_SEARCH, web_search_attempts=0)
        assert main_router(state) == WEB_SEARCH

    def test_web_search_exhausted_goes_to_failure(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=WEB_SEARCH, web_search_attempts=MAX_WEB_SEARCH)
        assert main_router(state) == FAILURE

    def test_routes_to_document_summarizer(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=DOCUMENT_SUMMARIZER)
        assert main_router(state) == DOCUMENT_SUMMARIZER

    def test_routes_to_global_summarizer(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=GLOBAL_SUMMARIZER)
        assert main_router(state) == GLOBAL_SUMMARIZER

    def test_routes_to_failure(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=FAILURE)
        assert main_router(state) == FAILURE

    def test_routes_to_sql_query(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=SQL_QUERY, sql_attempts=0)
        assert main_router(state) == SQL_QUERY

    def test_sql_exhausted_goes_to_answer(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=SQL_QUERY, sql_attempts=MAX_SQL_RETRIES)
        assert main_router(state) == ANSWER

    def test_none_action_defaults_to_answer(self):
        from agent.graph_nodes import main_router

        state = _make_state(action=None)
        assert main_router(state) == ANSWER


@pytest.mark.unit
class TestSummaryRouter:
    def test_routes_to_answer(self):
        from agent.graph_nodes import summary_router

        state = _make_state(after_summary=ANSWER)
        assert summary_router(state) == ANSWER

    def test_routes_to_generate(self):
        from agent.graph_nodes import summary_router

        state = _make_state(after_summary=GENERATE)
        assert summary_router(state) == GENERATE

    def test_default_is_answer(self):
        from agent.graph_nodes import summary_router

        state = _make_state(after_summary=None)
        assert summary_router(state) == ANSWER


@pytest.mark.unit
class TestFailureNode:
    @pytest.mark.asyncio
    async def test_sets_failure_message(self):
        from agent.graph_nodes import failure

        state = _make_state()
        result = await failure(state)
        assert "unable to answer" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_appends_to_messages(self):
        from agent.graph_nodes import failure

        state = _make_state()
        result = await failure(state)
        assert len(result.messages) == 1


@pytest.mark.unit
class TestSelfKnowledgeNode:
    @pytest.mark.asyncio
    async def test_external_mode_skips_self_knowledge(self):
        from agent.graph_nodes import self_knowledge

        state = _make_state(mode="External", answer="existing answer")
        result = await self_knowledge(state)
        assert result.answer == "existing answer"

    @pytest.mark.asyncio
    async def test_no_self_knowledge_flag_skips(self):
        from agent.graph_nodes import self_knowledge

        state = _make_state(
            mode="Internal", use_self_knowledge=False, answer="existing"
        )
        result = await self_knowledge(state)
        assert result.answer == "existing"

    @pytest.mark.asyncio
    async def test_empty_answer_gets_fallback(self):
        from agent.graph_nodes import self_knowledge

        state = _make_state(mode="External", answer="", use_self_knowledge=False)
        result = await self_knowledge(state)
        assert "unable to answer" in result.answer.lower()

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.invoke_llm", new_callable=AsyncMock)
    async def test_internal_with_self_knowledge(self, mock_llm):
        from agent.graph_nodes import self_knowledge
        from core.llm.outputs import SelfKnowledgeLLMOutput

        mock_llm.return_value = SelfKnowledgeLLMOutput(
            answer="AI is artificial intelligence"
        )
        state = _make_state(mode="Internal", use_self_knowledge=True)
        result = await self_knowledge(state)
        assert result.answer == "AI is artificial intelligence"


@pytest.mark.unit
class TestSqlQueryNode:
    @pytest.mark.asyncio
    async def test_no_query_returns_message(self):
        from agent.graph_nodes import sql_query_node

        state = _make_state(sql_query=None)
        result = await sql_query_node(state)
        assert "No SQL query" in result.sql_result

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.execute_sql_query", new_callable=AsyncMock)
    async def test_successful_query(self, mock_execute):
        from agent.graph_nodes import sql_query_node

        mock_execute.return_value = "col1|col2\n1|2"
        state = _make_state(sql_query="SELECT * FROM sheet1")
        result = await sql_query_node(state)
        assert result.sql_result == "col1|col2\n1|2"
        assert result.sql_attempts == 1

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.execute_sql_query", new_callable=AsyncMock)
    async def test_query_exception(self, mock_execute):
        from agent.graph_nodes import sql_query_node

        mock_execute.side_effect = Exception("SQL syntax error")
        state = _make_state(sql_query="BAD SQL")
        result = await sql_query_node(state)
        assert "SQL execution error" in result.sql_result
