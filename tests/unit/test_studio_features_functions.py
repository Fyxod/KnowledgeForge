"""
Comprehensive unit tests for ALL five studio feature modules:
  - insights, strategic_analysis, strategic_roadmap,
    technical_analysis, technical_roadmap

Covers: fetch_document_content (truncated + multi‑doc), word_count,
        build_*_prompt, generate_*.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from core.models.document import Document


# ── Helpers ──────────────────────────────────────────────────────────────


def _short_doc(doc_id="d1"):
    return Document(
        id=doc_id, type="pdf", file_name="t.pdf", title="Title", full_text="short text"
    )


def _long_doc_no_summary(doc_id="d1"):
    long_text = " ".join(["word"] * 10_000)
    return Document(
        id=doc_id, type="pdf", file_name="t.pdf", title="Title", full_text=long_text
    )


def _long_doc_with_summary(doc_id="d1"):
    long_text = " ".join(["word"] * 10_000)
    return Document(
        id=doc_id,
        type="pdf",
        file_name="t.pdf",
        title="Title",
        full_text=long_text,
        summary="Summary text",
    )


# ═══════════════════════════════════════════════════════════════════════
# INSIGHTS
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestInsightsFetchTruncated:
    def test_truncated_path(self):
        from core.studio_features.insights import fetch_document_content

        doc = _long_doc_no_summary()
        result = fetch_document_content(doc)
        # Should be truncated to 8000 words
        word_ct = len(result.split())
        assert word_ct <= 8010  # title adds a few

    def test_multi_doc(self):
        from core.studio_features.insights import fetch_document_content

        docs = [_short_doc("d1"), _short_doc("d2")]
        with patch(
            "core.studio_features.insights.compress_global_file_data",
            return_value=[
                {"title": "T1", "content": "C1"},
                {"title": "T2", "content": "C2"},
            ],
        ):
            result = fetch_document_content(docs)
        assert "T1" in result and "T2" in result


@pytest.mark.unit
class TestInsightsBuildPrompt:
    def test_returns_prompt(self):
        from core.studio_features.insights import build_insights_prompt

        result = build_insights_prompt("some document text")
        assert result is not None
        assert len(result) > 0


@pytest.mark.unit
class TestInsightsGenerate:
    @pytest.mark.asyncio
    async def test_generate_insights_calls_invoke(self):
        from core.studio_features.insights import generate_insights

        mock_output = MagicMock()
        with patch(
            "core.studio_features.insights.invoke_llm",
            new_callable=AsyncMock,
            return_value=mock_output,
        ):
            result = await generate_insights(_short_doc())
        assert result is mock_output

    @pytest.mark.asyncio
    async def test_generate_insights_multi_doc(self):
        from core.studio_features.insights import generate_insights

        mock_output = MagicMock()
        with (
            patch(
                "core.studio_features.insights.invoke_llm",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
            patch(
                "core.studio_features.insights.compress_global_file_data",
                return_value=[{"title": "T", "content": "C"}],
            ),
        ):
            result = await generate_insights([_short_doc()])
        assert result is mock_output


# ═══════════════════════════════════════════════════════════════════════
# STRATEGIC ANALYSIS
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestStrategicAnalysisFetch:
    def test_short_text(self):
        from core.studio_features.strategic_analysis import fetch_document_content

        doc = _short_doc()
        result = fetch_document_content(doc)
        assert "Title" in result and "short text" in result

    def test_summary_fallback(self):
        from core.studio_features.strategic_analysis import fetch_document_content

        doc = _long_doc_with_summary()
        result = fetch_document_content(doc)
        assert "Summary text" in result

    def test_truncated(self):
        from core.studio_features.strategic_analysis import fetch_document_content

        doc = _long_doc_no_summary()
        result = fetch_document_content(doc)
        assert len(result.split()) <= 8010

    def test_multi_doc(self):
        from core.studio_features.strategic_analysis import fetch_document_content

        docs = [_short_doc("d1"), _short_doc("d2")]
        with patch(
            "core.studio_features.strategic_analysis.compress_global_file_data",
            return_value=[
                {"title": "T1", "content": "C1"},
                {"title": "T2", "content": "C2"},
            ],
        ):
            result = fetch_document_content(docs)
        assert "T1" in result


@pytest.mark.unit
class TestStrategicAnalysisBuildPrompt:
    def test_returns_prompt(self):
        from core.studio_features.strategic_analysis import (
            build_strategic_analysis_prompt,
        )

        result = build_strategic_analysis_prompt("data")
        assert result is not None
        assert len(result) > 0


@pytest.mark.unit
class TestStrategicAnalysisGenerate:
    @pytest.mark.asyncio
    async def test_generate(self):
        from core.studio_features.strategic_analysis import generate_strategic_analysis

        mock_out = MagicMock()
        with patch(
            "core.studio_features.strategic_analysis.invoke_llm",
            new_callable=AsyncMock,
            return_value=mock_out,
        ):
            result = await generate_strategic_analysis(_short_doc())
        assert result is mock_out

    @pytest.mark.asyncio
    async def test_generate_multi(self):
        from core.studio_features.strategic_analysis import generate_strategic_analysis

        mock_out = MagicMock()
        with (
            patch(
                "core.studio_features.strategic_analysis.invoke_llm",
                new_callable=AsyncMock,
                return_value=mock_out,
            ),
            patch(
                "core.studio_features.strategic_analysis.compress_global_file_data",
                return_value=[{"title": "T", "content": "C"}],
            ),
        ):
            result = await generate_strategic_analysis([_short_doc()])
        assert result is mock_out


@pytest.mark.unit
class TestStrategicAnalysisWordCount:
    def test_word_count(self):
        from core.studio_features.strategic_analysis import word_count

        assert word_count("one two three") == 3


# ═══════════════════════════════════════════════════════════════════════
# STRATEGIC ROADMAP
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestStrategicRoadmapFetch:
    def test_short_text(self):
        from core.studio_features.strategic_roadmap import fetch_document_content

        doc = _short_doc()
        result = fetch_document_content(doc)
        assert "Title" in result

    def test_summary_fallback(self):
        from core.studio_features.strategic_roadmap import fetch_document_content

        doc = _long_doc_with_summary()
        result = fetch_document_content(doc)
        assert "Summary text" in result

    def test_truncated(self):
        from core.studio_features.strategic_roadmap import fetch_document_content

        doc = _long_doc_no_summary()
        result = fetch_document_content(doc)
        assert len(result.split()) <= 8010

    def test_multi_doc(self):
        from core.studio_features.strategic_roadmap import fetch_document_content

        docs = [_short_doc("d1"), _short_doc("d2")]
        with patch(
            "core.studio_features.strategic_roadmap.compress_global_file_data",
            return_value=[{"title": "A", "content": "B"}],
        ):
            result = fetch_document_content(docs)
        assert "A" in result


@pytest.mark.unit
class TestStrategicRoadmapBuildPrompt:
    def test_returns_prompt(self):
        from core.studio_features.strategic_roadmap import (
            build_strategic_roadmap_prompt,
        )

        result = build_strategic_roadmap_prompt("data", n_years=3)
        assert result is not None
        assert len(result) > 0


@pytest.mark.unit
class TestStrategicRoadmapGenerate:
    @pytest.mark.asyncio
    async def test_generate(self):
        from core.studio_features.strategic_roadmap import generate_strategic_roadmap

        mock_out = MagicMock()
        with patch(
            "core.studio_features.strategic_roadmap.invoke_llm",
            new_callable=AsyncMock,
            return_value=mock_out,
        ):
            result = await generate_strategic_roadmap(_short_doc(), n_years=5)
        assert result is mock_out


@pytest.mark.unit
class TestStrategicRoadmapWordCount:
    def test_word_count(self):
        from core.studio_features.strategic_roadmap import word_count

        assert word_count("a b c d") == 4


# ═══════════════════════════════════════════════════════════════════════
# TECHNICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestTechnicalAnalysisFetch:
    def test_short_text(self):
        from core.studio_features.technical_analysis import fetch_document_content

        result = fetch_document_content(_short_doc())
        assert "short text" in result

    def test_summary_fallback(self):
        from core.studio_features.technical_analysis import fetch_document_content

        result = fetch_document_content(_long_doc_with_summary())
        assert "Summary text" in result

    def test_truncated(self):
        from core.studio_features.technical_analysis import fetch_document_content

        result = fetch_document_content(_long_doc_no_summary())
        assert len(result.split()) <= 8010

    def test_multi_doc(self):
        from core.studio_features.technical_analysis import fetch_document_content

        with patch(
            "core.studio_features.technical_analysis.compress_global_file_data",
            return_value=[{"title": "X", "content": "Y"}],
        ):
            result = fetch_document_content([_short_doc()])
        assert "X" in result


@pytest.mark.unit
class TestTechnicalAnalysisBuildPrompt:
    def test_returns_prompt(self):
        from core.studio_features.technical_analysis import (
            build_technical_analysis_prompt,
        )

        result = build_technical_analysis_prompt("data")
        assert result is not None
        assert len(result) > 0


@pytest.mark.unit
class TestTechnicalAnalysisGenerate:
    @pytest.mark.asyncio
    async def test_generate(self):
        from core.studio_features.technical_analysis import generate_technical_analysis

        mock_out = MagicMock()
        with patch(
            "core.studio_features.technical_analysis.invoke_llm",
            new_callable=AsyncMock,
            return_value=mock_out,
        ):
            result = await generate_technical_analysis(_short_doc())
        assert result is mock_out

    @pytest.mark.asyncio
    async def test_generate_multi(self):
        from core.studio_features.technical_analysis import generate_technical_analysis

        mock_out = MagicMock()
        with (
            patch(
                "core.studio_features.technical_analysis.invoke_llm",
                new_callable=AsyncMock,
                return_value=mock_out,
            ),
            patch(
                "core.studio_features.technical_analysis.compress_global_file_data",
                return_value=[{"title": "T", "content": "C"}],
            ),
        ):
            result = await generate_technical_analysis([_short_doc()])
        assert result is mock_out


@pytest.mark.unit
class TestTechnicalAnalysisWordCount:
    def test_word_count(self):
        from core.studio_features.technical_analysis import word_count

        assert word_count("hello") == 1


# ═══════════════════════════════════════════════════════════════════════
# TECHNICAL ROADMAP
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestTechnicalRoadmapFetch:
    def test_short_text(self):
        from core.studio_features.technical_roadmap import fetch_document_content

        result = fetch_document_content(_short_doc())
        assert "short text" in result

    def test_summary_fallback(self):
        from core.studio_features.technical_roadmap import fetch_document_content

        result = fetch_document_content(_long_doc_with_summary())
        assert "Summary text" in result

    def test_truncated(self):
        from core.studio_features.technical_roadmap import fetch_document_content

        result = fetch_document_content(_long_doc_no_summary())
        assert len(result.split()) <= 8010

    def test_multi_doc(self):
        from core.studio_features.technical_roadmap import fetch_document_content

        with patch(
            "core.studio_features.technical_roadmap.compress_global_file_data",
            return_value=[{"title": "Z", "content": "W"}],
        ):
            result = fetch_document_content([_short_doc()])
        assert "Z" in result


@pytest.mark.unit
class TestTechnicalRoadmapBuildPrompt:
    def test_returns_prompt(self):
        from core.studio_features.technical_roadmap import (
            build_technical_roadmap_prompt,
        )

        result = build_technical_roadmap_prompt("data", n_years=5)
        assert result is not None
        assert len(result) > 0


@pytest.mark.unit
class TestTechnicalRoadmapGenerate:
    @pytest.mark.asyncio
    async def test_generate(self):
        from core.studio_features.technical_roadmap import generate_technical_roadmap

        mock_out = MagicMock()
        with patch(
            "core.studio_features.technical_roadmap.invoke_llm",
            new_callable=AsyncMock,
            return_value=mock_out,
        ):
            result = await generate_technical_roadmap(_short_doc(), n_years=3)
        assert result is mock_out


@pytest.mark.unit
class TestTechnicalRoadmapWordCount:
    def test_word_count(self):
        from core.studio_features.technical_roadmap import word_count

        assert word_count("") == 0
