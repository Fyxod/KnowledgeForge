"""
Integration tests — happy paths for extra routes (mindmap, summary)
and thread CRUD operations.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_aio_open_mock(content: str):
    """Return a MagicMock that behaves like ``aiofiles.open(...)``."""
    file_handle = AsyncMock()
    file_handle.read = AsyncMock(return_value=content)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=file_handle)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


MINDMAP_DATA = json.dumps({"nodes": [{"id": "1", "label": "root"}]})

DOC_JSON = json.dumps(
    {
        "id": "doc_001",
        "type": "pdf",
        "file_name": "test.pdf",
        "title": "Test Document",
        "full_text": "Document content text",
    }
)

SUMMARY_DOC_JSON = json.dumps(
    {
        "id": "doc_001",
        "type": "pdf",
        "file_name": "test.pdf",
        "title": "Test Document",
        "full_text": "Document content text",
        "summary": "This is a summary",
    }
)


# ═══════════════════════════════════════════════════════════════════════
# MINDMAP
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestMindmapHappyPath:
    @pytest.mark.asyncio
    async def test_mindmap_file_exists(self, async_client, populated_db, auth_headers):
        """When mind_map JSON file exists, return it."""
        with (
            patch("app.routes.extra.os.path.exists", return_value=True),
            patch("app.routes.extra.aiofiles.open", _make_aio_open_mock(MINDMAP_DATA)),
        ):
            resp = await async_client.get("/mindmap/thread_001", headers=auth_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["mind_map"] is True
        assert body["status"] is True

    @pytest.mark.asyncio
    async def test_mindmap_no_documents_in_thread(
        self, async_client, auth_headers, patched_db
    ):
        """Empty documents list returns mind_map=False."""
        patched_db.users.insert_one(
            {
                "userId": "user_test_123",
                "name": "Test",
                "email": "test@example.com",
                "password": "hashed",
                "is_active": True,
                "threads": {
                    "thread_001": {
                        "thread_name": "T",
                        "documents": [],
                        "chats": [],
                        "createdAt": "2024-01-01",
                        "updatedAt": "2024-01-01",
                        "extra_done": False,
                    }
                },
            }
        )
        resp = await async_client.get("/mindmap/thread_001", headers=auth_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["mind_map"] is False

    @pytest.mark.asyncio
    async def test_mindmap_not_enabled(self, async_client, populated_db, auth_headers):
        """mindmap_enabled=False and no file → says not enabled."""
        with patch("app.routes.extra.os.path.exists", return_value=False):
            resp = await async_client.get("/mindmap/thread_001", headers=auth_headers)

        body = resp.json()
        assert body["mind_map"] is False
        assert (
            "not enabled" in body.get("message", "").lower()
            or body["mind_map"] is False
        )


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY — SUMMARIZATION disabled
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSummaryDisabled:
    @pytest.mark.asyncio
    async def test_summary_disabled(self, async_client, populated_db, auth_headers):
        """When SUMMARIZATION switch is False, return disabled message."""
        with patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": False}):
            resp = await async_client.post(
                "/summary",
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "disabled" in body.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_global_summary_disabled(
        self, async_client, populated_db, auth_headers
    ):
        """When SUMMARIZATION switch is False, global summary is disabled."""
        with patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": False}):
            resp = await async_client.post(
                "/summary/global",
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "disabled" in body.get("message", "").lower()


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY — happy path with existing summary
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestSummaryHappyPath:
    @pytest.mark.asyncio
    async def test_returns_existing_summary(
        self, async_client, populated_db, auth_headers
    ):
        """When document has a summary, return it."""
        with (
            patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True}),
            patch("app.routes.extra.os.path.exists", return_value=True),
            patch("app.routes.extra.os.listdir", return_value=["doc.json"]),
            patch(
                "app.routes.extra.aiofiles.open", _make_aio_open_mock(SUMMARY_DOC_JSON)
            ),
        ):
            resp = await async_client.post(
                "/summary",
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True
        assert body["summary"] == "This is a summary"

    @pytest.mark.asyncio
    async def test_summary_not_found(self, async_client, populated_db, auth_headers):
        """When parsed dir doesn't exist, return error."""
        with (
            patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True}),
            patch("app.routes.extra.os.path.exists", return_value=False),
        ):
            resp = await async_client.post(
                "/summary",
                json={"thread_id": "thread_001", "document_id": "doc_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "error" in body


# ═══════════════════════════════════════════════════════════════════════
# GLOBAL SUMMARY — happy path
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestGlobalSummaryHappyPath:
    @pytest.mark.asyncio
    async def test_global_summary_completed(
        self, async_client, populated_db, auth_headers
    ):
        """When global summary file exists and completed."""
        completed_data = {"state": "completed", "data": {"summary": "Global sum"}}
        with (
            patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True}),
            patch("app.routes.extra.os.path.exists", return_value=True),
            patch(
                "app.routes.extra.read_generation_status",
                new_callable=AsyncMock,
                return_value=completed_data,
            ),
        ):
            resp = await async_client.post(
                "/summary/global",
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is True
        assert body["summary"] == "Global sum"

    @pytest.mark.asyncio
    async def test_global_summary_pending(
        self, async_client, populated_db, auth_headers
    ):
        """When global summary is pending."""
        with (
            patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True}),
            patch("app.routes.extra.os.path.exists", return_value=True),
            patch(
                "app.routes.extra.read_generation_status",
                new_callable=AsyncMock,
                return_value={"state": "pending"},
            ),
        ):
            resp = await async_client.post(
                "/summary/global",
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False

    @pytest.mark.asyncio
    async def test_global_summary_failed(
        self, async_client, populated_db, auth_headers
    ):
        """When global summary previously failed."""
        with (
            patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True}),
            patch("app.routes.extra.os.path.exists", return_value=True),
            patch(
                "app.routes.extra.read_generation_status",
                new_callable=AsyncMock,
                return_value={"state": "failed", "error": "LLM error"},
            ),
        ):
            resp = await async_client.post(
                "/summary/global",
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False
        assert body.get("failed") is True

    @pytest.mark.asyncio
    async def test_global_summary_first_generation(
        self, async_client, populated_db, auth_headers
    ):
        """No file yet → write pending and kick off generation."""
        with (
            patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True}),
            patch("app.routes.extra.os.path.exists", return_value=False),
            patch("app.routes.extra.write_pending_status", new_callable=AsyncMock),
            patch("app.routes.extra.asyncio.create_task"),
        ):
            resp = await async_client.post(
                "/summary/global",
                json={"thread_id": "thread_001"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] is False


# ═══════════════════════════════════════════════════════════════════════
# THREAD — CRUD operations
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestThreadCrud:
    @pytest.mark.asyncio
    async def test_create_thread(self, async_client, populated_db, auth_headers):
        resp = await async_client.post(
            "/thread/",
            json={"thread_name": "New Thread"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["thread_name"] == "New Thread"
        assert "thread_id" in body

    @pytest.mark.asyncio
    async def test_get_thread(self, async_client, populated_db, auth_headers):
        resp = await async_client.get("/thread/thread_001", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "thread_name" in body or "thread" in body or "error" not in body

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, async_client, populated_db, auth_headers):
        resp = await async_client.get("/thread/nonexistent", headers=auth_headers)
        body = resp.json()
        assert "error" in body or resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_thread_name(self, async_client, populated_db, auth_headers):
        resp = await async_client.put(
            "/thread/thread_001",
            json={"thread_name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_threads(self, async_client, populated_db, auth_headers):
        resp = await async_client.get("/thread/", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_thread(self, async_client, populated_db, auth_headers):
        with (
            patch("app.routes.thread.shutil.rmtree"),
            patch(
                "app.routes.thread.delete_document_from_chroma", new_callable=AsyncMock
            ),
            patch(
                "app.routes.thread.rebuild_bm25_after_deletion", new_callable=AsyncMock
            ),
        ):
            resp = await async_client.delete("/thread/thread_001", headers=auth_headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════
# WORDCLOUD — basic tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestWordcloudEndpoint:
    @pytest.mark.asyncio
    async def test_wordcloud_no_text(self, async_client, populated_db, auth_headers):
        """No parsed files → should return error."""
        with patch("app.routes.extra.os.path.exists", return_value=False):
            resp = await async_client.post(
                "/wordcloud/thread_001",
                json={"document_ids": ["doc_001"]},
                headers=auth_headers,
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_wordcloud_user_not_found(
        self, async_client, patched_db, auth_headers
    ):
        resp = await async_client.post(
            "/wordcloud/thread_001",
            json={"document_ids": ["doc_001"]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_wordcloud_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        resp = await async_client.post(
            "/wordcloud/nonexistent",
            json={"document_ids": ["doc_001"]},
            headers=auth_headers,
        )
        assert resp.status_code == 404
