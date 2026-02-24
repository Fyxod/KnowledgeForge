"""
Unit tests for agent.decomposition — query decomposition node.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.unit
class TestDecompositionNode:
    @pytest.mark.asyncio
    @patch("agent.decomposition.invoke_llm", new_callable=AsyncMock)
    async def test_no_decomposition(self, mock_llm):
        from agent.decomposition import decomposition_node
        from core.llm.outputs import DecompositionLLMOutput

        mock_llm.return_value = DecompositionLLMOutput(
            requires_decomposition=False,
            resolved_query="What is AI?",
            sub_queries=[],
        )
        result = await decomposition_node("What is AI?", [])
        assert result.requires_decomposition is False
        assert result.resolved_query == "What is AI?"

    @pytest.mark.asyncio
    @patch("agent.decomposition.invoke_llm", new_callable=AsyncMock)
    async def test_with_decomposition(self, mock_llm):
        from agent.decomposition import decomposition_node
        from core.llm.outputs import DecompositionLLMOutput

        mock_llm.return_value = DecompositionLLMOutput(
            requires_decomposition=True,
            resolved_query="Compare X and Y",
            sub_queries=["What is X?", "What is Y?"],
        )
        result = await decomposition_node("Compare X and Y", [])
        assert result.requires_decomposition is True
        assert len(result.sub_queries) == 2

    @pytest.mark.asyncio
    @patch("agent.decomposition.invoke_llm", new_callable=AsyncMock)
    async def test_with_spreadsheet_context(self, mock_llm):
        from agent.decomposition import decomposition_node
        from core.llm.outputs import DecompositionLLMOutput

        mock_llm.return_value = DecompositionLLMOutput(
            requires_decomposition=False,
            resolved_query="Show sales data",
            sub_queries=[],
        )
        result = await decomposition_node(
            "Show sales data",
            [],
            has_spreadsheet_data=True,
            spreadsheet_schema="CREATE TABLE sales(id INT, amount FLOAT)",
        )
        assert result.resolved_query == "Show sales data"

    @pytest.mark.asyncio
    @patch("agent.decomposition.invoke_llm", new_callable=AsyncMock)
    async def test_with_chat_history(self, mock_llm):
        from agent.decomposition import decomposition_node
        from core.llm.outputs import DecompositionLLMOutput
        from langchain_core.messages import HumanMessage, AIMessage

        mock_llm.return_value = DecompositionLLMOutput(
            requires_decomposition=False,
            resolved_query="Tell me more about that topic",
            sub_queries=[],
        )
        messages = [
            HumanMessage(content="What is ML?"),
            AIMessage(content="ML is..."),
        ]
        result = await decomposition_node("Tell me more", messages)
        assert result is not None
