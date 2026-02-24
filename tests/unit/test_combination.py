"""
Unit tests for agent.combination — answer combination node.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.unit
class TestCombinationNode:
    @pytest.mark.asyncio
    @patch("agent.combination.invoke_llm", new_callable=AsyncMock)
    async def test_combines_sub_answers(self, mock_llm):
        from agent.combination import combination_node
        from core.llm.outputs import CombinationLLMOutput

        mock_llm.return_value = CombinationLLMOutput(answer="Combined result")
        sub_answers = [
            {"sub_query": "Q1", "sub_answer": "A1"},
            {"sub_query": "Q2", "sub_answer": "A2"},
        ]
        result = await combination_node(sub_answers, "resolved", "original")
        assert result == "Combined result"
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch("agent.combination.invoke_llm", new_callable=AsyncMock)
    async def test_uses_original_when_resolved_is_none(self, mock_llm):
        from agent.combination import combination_node
        from core.llm.outputs import CombinationLLMOutput

        mock_llm.return_value = CombinationLLMOutput(answer="Answer")
        result = await combination_node([], None, "original query")
        assert result == "Answer"

    @pytest.mark.asyncio
    @patch("agent.combination.invoke_llm", new_callable=AsyncMock)
    async def test_empty_sub_answers(self, mock_llm):
        from agent.combination import combination_node
        from core.llm.outputs import CombinationLLMOutput

        mock_llm.return_value = CombinationLLMOutput(answer="No data")
        result = await combination_node([], "query", "query")
        assert result == "No data"
