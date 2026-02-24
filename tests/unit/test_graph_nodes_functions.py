"""
Unit tests for agent.graph_nodes — async node functions: retriever, generate,
web_search, document_summarizer, global_summarizer.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from agent.state import AgentState
from core.constants import (
    ANSWER,
    FAILURE,
    GENERATE,
    EXTERNAL,
    INTERNAL,
    DOCUMENT_SUMMARIZER,
    GLOBAL_SUMMARIZER,
)


def _make_state(**overrides):
    defaults = {
        "user_id": "u1",
        "thread_id": "t1",
        "query": "test query",
        "resolved_query": "test query",
        "original_query": "test query",
        "messages": [],
        "mode": EXTERNAL,
        "llm": {"model": "test", "port": 11434},
    }
    defaults.update(overrides)
    return AgentState(**defaults)


# ---------------------------------------------------------------------------
# retriever node
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRetrieverNode:
    @pytest.mark.asyncio
    @patch("agent.graph_nodes.rerank_chunks")
    @patch("agent.graph_nodes.get_thread_documents_retriever", new_callable=AsyncMock)
    async def test_retriever_high_confidence(self, mock_retriever, mock_rerank):
        from agent.graph_nodes import retriever

        docs = [
            {
                "page_content": f"text{i}",
                "metadata": {
                    "document_id": f"d{i % 3}",
                    "title": "Doc",
                    "page_no": i,
                    "file_name": "f.pdf",
                },
                "rerank_score": 0.8,
            }
            for i in range(10)
        ]
        mock_retriever.return_value = docs
        mock_rerank.return_value = docs

        state = _make_state()
        with patch("builtins.open", mock_open()):
            result = await retriever(state)

        assert len(result.chunks) == 10
        assert result.confidence_score == "high"

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.rerank_chunks")
    @patch("agent.graph_nodes.get_thread_documents_retriever", new_callable=AsyncMock)
    async def test_retriever_medium_confidence(self, mock_retriever, mock_rerank):
        from agent.graph_nodes import retriever

        docs = [
            {
                "page_content": "text",
                "metadata": {
                    "document_id": "d1",
                    "title": "Doc",
                    "page_no": 1,
                    "file_name": "f.pdf",
                },
                "rerank_score": 0.4,
            }
            for _ in range(4)
        ]
        mock_retriever.return_value = docs
        mock_rerank.return_value = docs

        state = _make_state()
        with patch("builtins.open", mock_open()):
            result = await retriever(state)

        assert result.confidence_score == "medium"

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.rerank_chunks")
    @patch("agent.graph_nodes.get_thread_documents_retriever", new_callable=AsyncMock)
    async def test_retriever_low_confidence(self, mock_retriever, mock_rerank):
        from agent.graph_nodes import retriever

        docs = [
            {
                "page_content": "text",
                "metadata": {
                    "document_id": "d1",
                    "title": "Doc",
                    "page_no": 1,
                    "file_name": "f.pdf",
                },
                "rerank_score": 0.1,
            }
        ]
        mock_retriever.return_value = docs
        mock_rerank.return_value = docs

        state = _make_state()
        with patch("builtins.open", mock_open()):
            result = await retriever(state)

        assert result.confidence_score == "low"

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.rerank_chunks")
    @patch("agent.graph_nodes.get_thread_documents_retriever", new_callable=AsyncMock)
    async def test_retriever_empty_results(self, mock_retriever, mock_rerank):
        from agent.graph_nodes import retriever

        mock_retriever.return_value = []
        mock_rerank.return_value = []

        state = _make_state()
        with patch("builtins.open", mock_open()):
            result = await retriever(state)

        assert result.chunks == []
        assert result.confidence_score == "low"


# ---------------------------------------------------------------------------
# generate node
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestGenerateNode:
    @pytest.mark.asyncio
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.invoke_llm", new_callable=AsyncMock)
    @patch("agent.graph_nodes.build_main_prompt")
    async def test_generate_success_external(self, mock_prompt, mock_llm, mock_aio):
        from agent.graph_nodes import generate
        from core.llm.outputs import MainLLMOutputExternal

        mock_prompt.return_value = "prompt text"
        mock_file = AsyncMock()
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_llm.return_value = {
            "answer": "Generated answer",
            "action": ANSWER,
            "chunks_used": [
                {"document_id": "d1", "page_no": 1, "title": "Doc1"},
                {"document_id": "d2", "page_no": 2, "title": "Doc2"},
            ],
            "suggested_questions": ["Q1?"],
            "web_search_queries": [],
        }

        state = _make_state(mode=EXTERNAL)
        result = await generate(state)

        assert result.answer == "Generated answer"
        assert result.action == ANSWER
        assert result.attempts == 1

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.invoke_llm", new_callable=AsyncMock)
    @patch("agent.graph_nodes.build_main_prompt")
    async def test_generate_success_internal(self, mock_prompt, mock_llm, mock_aio):
        from agent.graph_nodes import generate

        mock_prompt.return_value = "prompt text"
        mock_file = AsyncMock()
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_llm.return_value = {
            "answer": "Internal answer",
            "action": ANSWER,
            "chunks_used": [],
            "document_id": None,
        }

        state = _make_state(mode=INTERNAL, use_self_knowledge=False)
        result = await generate(state)

        assert result.answer == "Internal answer"

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.asyncio.sleep", new_callable=AsyncMock)
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.invoke_llm", new_callable=AsyncMock)
    @patch("agent.graph_nodes.build_main_prompt")
    async def test_generate_all_retries_fail(
        self, mock_prompt, mock_llm, mock_aio, mock_sleep
    ):
        from agent.graph_nodes import generate

        mock_prompt.return_value = "prompt text"
        mock_file = AsyncMock()
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_llm.side_effect = Exception("LLM error")

        state = _make_state()
        result = await generate(state)

        assert result.action == FAILURE
        assert "error occurred" in result.answer.lower()


# ---------------------------------------------------------------------------
# web_search node
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestWebSearchNode:
    @pytest.mark.asyncio
    @patch("agent.graph_nodes.parallel_search", new_callable=AsyncMock)
    async def test_web_search_success(self, mock_search):
        from agent.graph_nodes import web_search

        mock_search.return_value = [
            {"title": "Result 1", "content": "Content 1", "url": "http://example.com"}
        ]

        state = _make_state(web_search_queries=["python tutorial"])
        result = await web_search(state)

        assert result.web_search is True
        assert result.web_search_attempts == 1
        assert len(result.web_search_results) == 1

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.asyncio.sleep", new_callable=AsyncMock)
    @patch("agent.graph_nodes.parallel_search", new_callable=AsyncMock)
    async def test_web_search_all_retries_fail(self, mock_search, mock_sleep):
        from agent.graph_nodes import web_search

        mock_search.side_effect = Exception("Network error")

        state = _make_state(web_search_queries=["query"])
        result = await web_search(state)

        assert result.web_search is False
        assert result.web_search_results == []


# ---------------------------------------------------------------------------
# document_summarizer node
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestDocumentSummarizerNode:
    @pytest.mark.asyncio
    async def test_no_document_id(self):
        from agent.graph_nodes import document_summarizer

        state = _make_state(document_id=None, chunks=[])
        result = await document_summarizer(state)
        assert "No summary available" in result.summary

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.os.path.exists", return_value=True)
    @patch("agent.graph_nodes.os.makedirs")
    async def test_document_with_summary(self, mock_makedirs, mock_exists, mock_aio):
        from agent.graph_nodes import document_summarizer

        doc_json = json.dumps({"summary": "This is the summary."})
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=doc_json)
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        state = _make_state(
            document_id="doc1",
            chunks=[
                {
                    "document_id": "doc1",
                    "title": "Test Doc",
                    "file_name": "test.pdf",
                    "content": "some content",
                    "page_no": 1,
                    "metadata": {},
                }
            ],
        )
        result = await document_summarizer(state)
        assert "summary" in result.answer.lower()
        assert result.after_summary == ANSWER

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.os.path.exists", return_value=True)
    @patch("agent.graph_nodes.os.makedirs")
    async def test_document_without_summary(self, mock_makedirs, mock_exists, mock_aio):
        from agent.graph_nodes import document_summarizer

        doc_json = json.dumps({"summary": ""})
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=doc_json)
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        state = _make_state(
            document_id="doc1",
            chunks=[
                {
                    "document_id": "doc1",
                    "title": "Test Doc",
                    "file_name": "test.pdf",
                    "content": "some content",
                    "page_no": 1,
                    "metadata": {},
                }
            ],
        )
        result = await document_summarizer(state)
        assert result.after_summary == GENERATE

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.os.path.exists", return_value=False)
    @patch("agent.graph_nodes.os.makedirs")
    async def test_document_parsed_file_missing(self, mock_makedirs, mock_exists):
        from agent.graph_nodes import document_summarizer

        state = _make_state(
            document_id="doc1",
            chunks=[
                {
                    "document_id": "doc1",
                    "title": "Test",
                    "file_name": "test.pdf",
                    "content": "c",
                    "page_no": 1,
                    "metadata": {},
                }
            ],
        )
        result = await document_summarizer(state)
        # No file found, state unchanged for summary
        assert result is not None


# ---------------------------------------------------------------------------
# global_summarizer node
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestGlobalSummarizerNode:
    @pytest.mark.asyncio
    @patch("agent.graph_nodes.os.path.exists", return_value=False)
    @patch("agent.graph_nodes.os.makedirs")
    async def test_no_global_summary_file(self, mock_makedirs, mock_exists):
        from agent.graph_nodes import global_summarizer

        state = _make_state()
        result = await global_summarizer(state)
        assert "No global summary" in result.summary
        assert result.after_summary == GENERATE

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.os.path.exists", return_value=True)
    @patch("agent.graph_nodes.os.makedirs")
    async def test_with_global_summary(self, mock_makedirs, mock_exists, mock_aio):
        from agent.graph_nodes import global_summarizer

        summary_json = json.dumps({"summary": "Global overview of all docs."})
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=summary_json)
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        state = _make_state()
        result = await global_summarizer(state)
        assert "Global overview" in result.answer
        assert result.after_summary == ANSWER

    @pytest.mark.asyncio
    @patch("agent.graph_nodes.aiofiles.open")
    @patch("agent.graph_nodes.os.path.exists", return_value=True)
    @patch("agent.graph_nodes.os.makedirs")
    async def test_with_empty_global_summary(
        self, mock_makedirs, mock_exists, mock_aio
    ):
        from agent.graph_nodes import global_summarizer

        summary_json = json.dumps({"summary": ""})
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=summary_json)
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        state = _make_state()
        result = await global_summarizer(state)
        assert "No global summary" in result.summary
        assert result.after_summary == GENERATE
