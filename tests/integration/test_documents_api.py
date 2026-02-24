"""
Integration tests for /data (document serving) API.
"""

import os
import pytest
from unittest.mock import patch


@pytest.mark.integration
class TestDocumentServing:
    @pytest.mark.asyncio
    async def test_get_document_no_token(self, async_client, patched_db):
        response = await async_client.get(
            "/data/user_test_123/threads/thread_001/uploads/test_doc.pdf"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_document_wrong_user(
        self, async_client, populated_db, auth_headers
    ):
        """Token's userId doesn't match the URL userId → 403."""
        response = await async_client.get(
            "/data/someone_else/threads/thread_001/uploads/test_doc.pdf",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_document_not_found_in_db(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.get(
            "/data/user_test_123/threads/thread_001/uploads/missing.pdf",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_document_path_traversal(
        self, async_client, populated_db, auth_headers
    ):
        """Path traversal attempt should be rejected."""
        response = await async_client.get(
            "/data/user_test_123/threads/thread_001/uploads/../../etc/passwd",
            headers=auth_headers,
        )
        # Should get 400 (invalid file name) or 404
        assert response.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_get_document_file_missing_on_disk(
        self, async_client, populated_db, auth_headers, tmp_path
    ):
        """Document exists in DB but file is missing on disk → 404."""
        with patch("app.routes.documents.os.path.exists", return_value=False):
            response = await async_client.get(
                "/data/user_test_123/threads/thread_001/uploads/test_doc.pdf",
                headers=auth_headers,
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_document_via_query_token(
        self, async_client, populated_db, auth_token, tmp_path
    ):
        """Auth via ?token= query param (for downloads)."""
        with patch("app.routes.documents.os.path.exists", return_value=False):
            response = await async_client.get(
                f"/data/user_test_123/threads/thread_001/uploads/test_doc.pdf?token={auth_token}",
            )
            assert response.status_code == 404  # file not on disk, but auth passed
