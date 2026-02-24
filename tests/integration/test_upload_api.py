"""
Integration tests for /upload API endpoint.
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.models.document import Document, Documents, Page


@pytest.mark.integration
class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_no_auth(self, async_client, patched_db):
        response = await async_client.post("/upload/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_create_empty_thread(
        self, async_client, populated_db, auth_headers
    ):
        """No files, but thread_name → should create an empty thread."""
        response = await async_client.post(
            "/upload/",
            data={"thread_name": "Empty Thread"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["documents"] == []
        assert "thread_id" in data

    @pytest.mark.asyncio
    async def test_upload_existing_thread_no_files(
        self, async_client, populated_db, auth_headers
    ):
        """No files + existing thread_id → return existing thread."""
        response = await async_client.post(
            "/upload/",
            data={"thread_id": "thread_001"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["thread_id"] == "thread_001"

    @pytest.mark.asyncio
    async def test_upload_no_files_no_thread(
        self, async_client, populated_db, auth_headers
    ):
        """No files, no thread_name, no thread_id → error."""
        response = await async_client.post(
            "/upload/",
            data={},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    @patch("app.routes.upload.save_documents_to_store", new_callable=AsyncMock)
    @patch("app.routes.upload.summarize_documents", new_callable=AsyncMock)
    @patch("app.routes.upload.create_stop_words")
    @patch("app.routes.upload.process_files", new_callable=AsyncMock)
    @patch("app.routes.upload.upload_files", new_callable=AsyncMock)
    @patch("app.routes.upload.mark_extra_done")
    async def test_upload_with_file(
        self,
        mock_mark,
        mock_upload_files,
        mock_process,
        mock_stop_words,
        mock_summarize,
        mock_save_docs,
        async_client,
        populated_db,
        auth_headers,
    ):
        """Upload a file to existing thread — full pipeline mocked."""
        # Configure mocks
        mock_upload_files.return_value = [
            {"file_name": "test.pdf", "file_path": "/tmp/test.pdf"}
        ]
        fake_doc = Document(
            id="doc_new",
            type="pdf",
            file_name="test.pdf",
            content=[Page(number=1, text="Hello world")],
            title="Test PDF",
            full_text="Hello world",
        )
        mock_process.return_value = Documents(
            documents=[fake_doc],
            thread_id="thread_001",
            user_id="user_test_123",
        )

        file_content = b"fake pdf content"
        response = await async_client.post(
            "/upload/",
            data={"thread_id": "thread_001"},
            files={"files": ("test.pdf", io.BytesIO(file_content), "application/pdf")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["documents"]) == 1
        assert data["documents"][0]["title"] == "Test PDF"

    @pytest.mark.asyncio
    async def test_upload_nonexistent_thread(
        self, async_client, populated_db, auth_headers
    ):
        """Attempt upload to non-existent thread_id → error."""
        response = await async_client.post(
            "/upload/",
            data={"thread_id": "nonexistent_thread"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_upload_user_not_found(self, async_client, patched_db, auth_headers):
        """User from JWT doesn't exist in DB."""
        response = await async_client.post(
            "/upload/",
            data={"thread_name": "Ghost"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data
