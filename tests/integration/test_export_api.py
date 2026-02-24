"""
Integration tests for /export API endpoints — markdown and HTML export.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


@pytest.mark.integration
class TestExportMarkdown:
    @pytest.mark.asyncio
    async def test_export_markdown_success(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.get(
            "/export/thread_001/markdown",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")
        assert "Content-Disposition" in response.headers
        assert response.text  # Non-empty

    @pytest.mark.asyncio
    async def test_export_markdown_no_auth(self, async_client, patched_db):
        response = await async_client.get("/export/thread_001/markdown")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_markdown_user_not_found(
        self, async_client, patched_db, auth_headers
    ):
        response = await async_client.get(
            "/export/thread_001/markdown", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_markdown_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.get(
            "/export/nonexistent/markdown", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_markdown_empty_chats(
        self, async_client, patched_db, auth_headers
    ):
        """Thread exists but has no chats → returns 'No messages' markdown."""
        from tests.factories import make_user, make_thread

        empty_thread = make_thread(name="Empty", chats=[])
        user = make_user(
            user_id="user_test_123",
            email="test@example.com",
            threads={"thread_empty": empty_thread},
        )
        patched_db.users.insert_one(user)

        response = await async_client.get(
            "/export/thread_empty/markdown", headers=auth_headers
        )
        assert response.status_code == 200
        assert "No messages" in response.text


@pytest.mark.integration
class TestExportHTML:
    @pytest.mark.asyncio
    async def test_export_html_success(self, async_client, populated_db, auth_headers):
        response = await async_client.get(
            "/export/thread_001/html",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "<html>" in response.text.lower()

    @pytest.mark.asyncio
    async def test_export_html_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.get(
            "/export/nonexistent/html", headers=auth_headers
        )
        assert response.status_code == 404
