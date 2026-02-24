"""
Unit tests for core.constants — feature switches and configuration constants.
"""

import pytest


@pytest.mark.unit
class TestSwitches:
    def test_switches_is_dict(self):
        from core.constants import SWITCHES

        assert isinstance(SWITCHES, dict)

    def test_expected_keys_present(self):
        from core.constants import SWITCHES

        expected_keys = [
            "MIND_MAP",
            "SUMMARIZATION",
            "FALLBACK_TO_GEMINI",
            "FALLBACK_TO_OPENAI",
            "DECOMPOSITION",
            "REMOTE_GPU",
        ]
        for key in expected_keys:
            assert key in SWITCHES

    def test_values_are_bool(self):
        from core.constants import SWITCHES

        for key, val in SWITCHES.items():
            assert isinstance(val, bool), f"SWITCHES[{key}] should be bool"


@pytest.mark.unit
class TestConstants:
    def test_chunk_count_positive(self):
        from core.constants import CHUNK_COUNT

        assert CHUNK_COUNT > 0

    def test_max_web_search_positive(self):
        from core.constants import MAX_WEB_SEARCH

        assert MAX_WEB_SEARCH > 0

    def test_max_sql_retries_positive(self):
        from core.constants import MAX_SQL_RETRIES

        assert MAX_SQL_RETRIES > 0

    def test_graph_node_names_are_strings(self):
        from core.constants import (
            RETRIEVER,
            GENERATE,
            WEB_SEARCH,
            ANSWER,
            ROUTER,
            FAILURE,
            GLOBAL_SUMMARIZER,
            DOCUMENT_SUMMARIZER,
            SELF_KNOWLEDGE,
            SQL_QUERY,
        )

        names = [
            RETRIEVER,
            GENERATE,
            WEB_SEARCH,
            ANSWER,
            ROUTER,
            FAILURE,
            GLOBAL_SUMMARIZER,
            DOCUMENT_SUMMARIZER,
            SELF_KNOWLEDGE,
            SQL_QUERY,
        ]
        for name in names:
            assert isinstance(name, str)
            assert len(name) > 0

    def test_mode_constants(self):
        from core.constants import INTERNAL, EXTERNAL

        assert INTERNAL == "Internal"
        assert EXTERNAL == "External"

    def test_gpu_configs_have_model_and_port(self):
        from core.constants import GPU_QUERY_LLM, GPU_COMBINATION_LLM

        assert hasattr(GPU_QUERY_LLM, "model")
        assert hasattr(GPU_QUERY_LLM, "port")
        assert isinstance(GPU_QUERY_LLM.port, int)
