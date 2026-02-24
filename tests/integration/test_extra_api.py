"""
Integration tests for /wordcloud, /mindmap, /summary, /summary/global endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import io


@pytest.mark.integration
class TestWordCloud:
    @pytest.mark.asyncio
    async def test_wordcloud_no_auth(self, async_client, patched_db):
        response = await async_client.post(
            "/wordcloud/thread_001",
            json={"document_ids": ["doc_001"]},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_wordcloud_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/wordcloud/nonexistent",
            json={"document_ids": ["doc_001"]},
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestMindMap:
    @pytest.mark.asyncio
    async def test_mindmap_no_auth(self, async_client, patched_db):
        response = await async_client.get("/mindmap/thread_001")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mindmap_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.get("/mindmap/nonexistent", headers=auth_headers)
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_mindmap_no_documents(self, async_client, patched_db, auth_headers):
        """Thread with no documents returns mind_map: False."""
        from tests.factories import make_user, make_thread

        user = make_user(
            user_id="user_test_123",
            email="test@example.com",
            threads={"thread_empty": make_thread(documents=[])},
        )
        patched_db.users.insert_one(user)

        response = await async_client.get("/mindmap/thread_empty", headers=auth_headers)
        data = response.json()
        assert data.get("mind_map") is False


@pytest.mark.integration
class TestSummary:
    @pytest.mark.asyncio
    async def test_summary_no_auth(self, async_client, patched_db):
        response = await async_client.post(
            "/summary",
            json={"thread_id": "t1", "document_id": "d1"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True, "MIND_MAP": True})
    async def test_summary_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/summary",
            json={"thread_id": "nonexistent", "document_id": "d1"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    @patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": False, "MIND_MAP": False})
    async def test_summary_feature_disabled(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/summary",
            json={"thread_id": "thread_001", "document_id": "doc_001"},
            headers=auth_headers,
        )
        data = response.json()
        assert "disabled" in data.get("message", "").lower()


@pytest.mark.integration
class TestGlobalSummary:
    @pytest.mark.asyncio
    async def test_global_summary_no_auth(self, async_client, patched_db):
        response = await async_client.post(
            "/summary/global",
            json={"thread_id": "t1"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": True, "MIND_MAP": True})
    async def test_global_summary_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/summary/global",
            json={"thread_id": "nonexistent"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    @patch("app.routes.extra.SWITCHES", {"SUMMARIZATION": False, "MIND_MAP": False})
    async def test_global_summary_feature_disabled(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/summary/global",
            json={"thread_id": "thread_001"},
            headers=auth_headers,
        )
        data = response.json()
        assert "disabled" in data.get("message", "").lower()
