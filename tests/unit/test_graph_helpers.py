"""
Unit tests for agent.graph_helpers — prompt builders and utility functions.
"""

import pytest
from unittest.mock import MagicMock


@pytest.mark.unit
class TestGetRecentHistory:
    def test_empty_history(self):
        from agent.graph_helpers import get_recent_history

        result = get_recent_history([], turns=2)
        assert result == []

    def test_short_history_returns_all(self):
        from agent.graph_helpers import get_recent_history

        history = [{"role": "user"}, {"role": "ai"}]
        result = get_recent_history(history, turns=2)
        assert len(result) == 2

    def test_exact_match_returns_all(self):
        from agent.graph_helpers import get_recent_history

        history = [{"role": "user"}, {"role": "ai"}, {"role": "user"}, {"role": "ai"}]
        result = get_recent_history(history, turns=2)
        assert len(result) == 4

    def test_truncates_to_recent_turns(self):
        from agent.graph_helpers import get_recent_history

        messages = []
        for i in range(10):
            messages.append({"role": "user", "content": f"msg_{i}"})
            messages.append({"role": "ai", "content": f"reply_{i}"})
        result = get_recent_history(messages, turns=2)
        assert len(result) == 4
        assert result[0]["content"] == "msg_8"

    def test_single_turn(self):
        from agent.graph_helpers import get_recent_history

        messages = [{"role": "user"}, {"role": "ai"}, {"role": "user"}, {"role": "ai"}]
        result = get_recent_history(messages, turns=1)
        assert len(result) == 2


@pytest.mark.unit
class TestParallelSearch:
    @pytest.mark.asyncio
    async def test_runs_queries_in_parallel(self):
        from agent.graph_helpers import parallel_search
        from unittest.mock import AsyncMock

        mock_tool = AsyncMock(side_effect=lambda q: f"result_{q}")
        queries = ["q1", "q2", "q3"]
        results = await parallel_search(queries, mock_tool)
        assert results == ["result_q1", "result_q2", "result_q3"]
        assert mock_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_empty_queries(self):
        from agent.graph_helpers import parallel_search
        from unittest.mock import AsyncMock

        mock_tool = AsyncMock()
        results = await parallel_search([], mock_tool)
        assert results == []
        assert mock_tool.call_count == 0


@pytest.mark.unit
class TestBuildMainPrompt:
    def test_returns_nonempty(self):
        from agent.graph_helpers import build_main_prompt
        from agent.state import AgentState

        state = AgentState(
            user_id="u1",
            thread_id="t1",
            query="What is this?",
            resolved_query="What is this?",
            original_query="What is this?",
            messages=[],
            mode="External",
            llm={"model": "test", "port": 11434},
        )
        result = build_main_prompt(state)
        assert result is not None


@pytest.mark.unit
class TestBuildSelfKnowledgePrompt:
    def test_returns_nonempty(self):
        from agent.graph_helpers import build_self_knowledge_prompt
        from agent.state import AgentState

        state = AgentState(
            user_id="u1",
            thread_id="t1",
            query="What is AI?",
            resolved_query="What is AI?",
            original_query="What is AI?",
            messages=[],
            mode="Internal",
            llm={"model": "test", "port": 11434},
        )
        result = build_self_knowledge_prompt(state)
        assert result is not None
