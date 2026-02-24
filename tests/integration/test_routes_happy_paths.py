"""
Integration tests — happy-path scenarios for studio-feature routes.

Each route follows the same generate-or-poll pattern.  We mock the
file-system layer (os.path.exists, os.listdir, aiofiles.open) and
read_generation_status so that the route returns completed data, a
pending indicator, or a failure response.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────

DOC_JSON = json.dumps(
    {
        "id": "doc_001",
        "type": "pdf",
        "file_name": "test.pdf",
        "title": "Test Document",
        "full_text": "Document content text for testing",
    }
)


def _make_aio_open_mock(content: str = DOC_JSON):
    """Return a MagicMock that behaves like ``aiofiles.open(...)``."""
    file_handle = AsyncMock()
    file_handle.read = AsyncMock(return_value=content)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=file_handle)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


# (route_module, single_endpoint, global_endpoint, result_key)
FEATURES = [
    ("app.routes.insights", "/insights", "/insights/global", "insights"),
    (
        "app.routes.strategic_analysis",
        "/strategic_analysis",
        "/strategic_analysis/global",
        "strategic_analysis",
    ),
    (
        "app.routes.strategic_roadmap",
        "/strategic_roadmap",
        "/strategic_roadmap/global",
        "strategic_roadmap",
    ),
    (
        "app.routes.technical_analysis",
        "/technical_analysis",
        "/technical_analysis/global",
        "technical_analysis",
    ),
    (
        "app.routes.technical_roadmap",
        "/technical_roadmap",
        "/technical_roadmap/global",
        "technical_roadmap",
    ),
]


# ═══════════════════════════════════════════════════════════════════════
#  SINGLE-DOCUMENT — completed
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSingleDocCompleted:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mod,endpoint,_gep,result_key", FEATURES)
    async def test_returns_completed(
        self,
        mod,
        endpoint,
        _gep,
        result_key,
        async_client,
        populated_db,
        auth_headers,
    ):
        completed_data = {"state": "completed", "data": {"key": "value"}}

        with (
            patch(f"{mod}.os.path.exists", return_value=True),
            patch(f"{mod}.os.listdir", return_value=["doc_001.json"]),
            patch(f"{mod}.os.makedirs"),
            patch(f"{mod}.aiofiles.open", _make_aio_open_mock()),
            patch(
                f"{mod}.read_generation_status",
                new_callable=AsyncMock,
                return_value=completed_data,
            ),
        ):
            resp = await async_client.post(
                endpoint,
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True
        assert result_key in body


# ═══════════════════════════════════════════════════════════════════════
#  SINGLE-DOCUMENT — pending
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSingleDocPending:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mod,endpoint,_gep,result_key", FEATURES)
    async def test_returns_pending(
        self,
        mod,
        endpoint,
        _gep,
        result_key,
        async_client,
        populated_db,
        auth_headers,
    ):
        pending_data = {"state": "pending"}

        with (
            patch(f"{mod}.os.path.exists", return_value=True),
            patch(f"{mod}.os.listdir", return_value=["doc_001.json"]),
            patch(f"{mod}.os.makedirs"),
            patch(f"{mod}.aiofiles.open", _make_aio_open_mock()),
            patch(
                f"{mod}.read_generation_status",
                new_callable=AsyncMock,
                return_value=pending_data,
            ),
        ):
            resp = await async_client.post(
                endpoint,
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert "message" in body or "Generating" in body.get("message", "")


# ═══════════════════════════════════════════════════════════════════════
#  SINGLE-DOCUMENT — failed
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSingleDocFailed:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mod,endpoint,_gep,result_key", FEATURES)
    async def test_returns_failed(
        self,
        mod,
        endpoint,
        _gep,
        result_key,
        async_client,
        populated_db,
        auth_headers,
    ):
        failed_data = {"state": "failed", "error": "Something went wrong"}

        with (
            patch(f"{mod}.os.path.exists", return_value=True),
            patch(f"{mod}.os.listdir", return_value=["doc_001.json"]),
            patch(f"{mod}.os.makedirs"),
            patch(f"{mod}.aiofiles.open", _make_aio_open_mock()),
            patch(
                f"{mod}.read_generation_status",
                new_callable=AsyncMock,
                return_value=failed_data,
            ),
        ):
            resp = await async_client.post(
                endpoint,
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert body.get("failed") is True


# ═══════════════════════════════════════════════════════════════════════
#  SINGLE-DOCUMENT — first generation (no status file yet)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSingleDocFirstGeneration:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mod,endpoint,_gep,result_key", FEATURES)
    async def test_kicks_off_generation(
        self,
        mod,
        endpoint,
        _gep,
        result_key,
        async_client,
        populated_db,
        auth_headers,
    ):
        # exists returns True for parsed_dir but read_generation returns None
        # (no status file yet) → should write pending and start generation
        with (
            patch(f"{mod}.os.path.exists") as mock_exists,
            patch(f"{mod}.os.listdir", return_value=["doc_001.json"]),
            patch(f"{mod}.os.makedirs"),
            patch(f"{mod}.aiofiles.open", _make_aio_open_mock()),
            patch(
                f"{mod}.read_generation_status",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(f"{mod}.write_pending_status", new_callable=AsyncMock),
            patch(f"{mod}.asyncio.create_task"),
        ):
            # parsed_dir exists, insights file does not
            mock_exists.side_effect = lambda p: "parsed" in str(p)
            resp = await async_client.post(
                endpoint,
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert "message" in body


# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL — completed
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestGlobalCompleted:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mod,_ep,global_ep,result_key", FEATURES)
    async def test_global_completed(
        self,
        mod,
        _ep,
        global_ep,
        result_key,
        async_client,
        populated_db,
        auth_headers,
    ):
        completed_data = {"state": "completed", "data": {"key": "global_result"}}

        with (
            patch(f"{mod}.os.path.exists", return_value=True),
            patch(f"{mod}.os.listdir", return_value=["doc_001.json"]),
            patch(f"{mod}.os.makedirs"),
            patch(f"{mod}.aiofiles.open", _make_aio_open_mock()),
            patch(
                f"{mod}.read_generation_status",
                new_callable=AsyncMock,
                return_value=completed_data,
            ),
        ):
            resp = await async_client.post(
                global_ep,
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True
        assert result_key in body


# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL — no documents found
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestGlobalNoDocs:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mod,_ep,global_ep,result_key", FEATURES)
    async def test_global_no_docs(
        self,
        mod,
        _ep,
        global_ep,
        result_key,
        async_client,
        populated_db,
        auth_headers,
    ):
        with patch(f"{mod}.os.path.exists", return_value=False):
            resp = await async_client.post(
                global_ep,
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 404
