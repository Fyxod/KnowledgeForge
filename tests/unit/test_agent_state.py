"""
Unit tests for agent.state — AgentState pydantic model.
"""

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestAgentState:
    def test_minimal_creation(self):
        from agent.state import AgentState

        state = AgentState(
            user_id="u1",
            thread_id="t1",
            query="q",
            resolved_query="q",
            original_query="q",
            messages=[],
            mode="External",
        )
        assert state.user_id == "u1"
        assert state.mode == "External"

    def test_defaults(self):
        from agent.state import AgentState

        state = AgentState(
            user_id="u1",
            thread_id="t1",
            query="q",
            resolved_query="q",
            original_query="q",
            messages=[],
            mode="Internal",
        )
        assert state.chunks == []
        assert state.web_search is False
        assert state.attempts == 0
        assert state.answer is None
        assert state.confidence_score is None
        assert state.sql_attempts == 0

    def test_invalid_mode_raises(self):
        from agent.state import AgentState

        with pytest.raises(ValidationError):
            AgentState(
                user_id="u1",
                thread_id="t1",
                query="q",
                resolved_query="q",
                original_query="q",
                messages=[],
                mode="InvalidMode",
            )

    def test_with_llm_config(self):
        from agent.state import AgentState

        state = AgentState(
            user_id="u1",
            thread_id="t1",
            query="q",
            resolved_query="q",
            original_query="q",
            messages=[],
            mode="External",
            llm={"model": "qwen3:14b", "port": 11434},
        )
        assert state.llm.model == "qwen3:14b"
        assert state.llm.port == 11434

    def test_mutable_fields(self):
        from agent.state import AgentState

        state = AgentState(
            user_id="u1",
            thread_id="t1",
            query="q",
            resolved_query="q",
            original_query="q",
            messages=[],
            mode="External",
        )
        state.chunks.append({"content": "test"})
        state.attempts = 3
        state.answer = "result"
        assert len(state.chunks) == 1
        assert state.attempts == 3
        assert state.answer == "result"
