"""
Integration tests for /thread API — CRUD, documents, chats, instructions.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
class TestCreateThread:
    @pytest.mark.asyncio
    async def test_create_thread_success(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/thread/",
            json={"thread_name": "New Thread"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["thread_name"] == "New Thread"
        assert "thread_id" in data

    @pytest.mark.asyncio
    async def test_create_thread_no_auth(self, async_client, patched_db):
        response = await async_client.post("/thread/", json={"thread_name": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_thread_user_not_found(
        self, async_client, patched_db, auth_headers
    ):
        # DB has no users
        response = await async_client.post(
            "/thread/",
            json={"thread_name": "Ghost"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data


@pytest.mark.integration
class TestGetThread:
    @pytest.mark.asyncio
    async def test_get_thread_success(self, async_client, populated_db, auth_headers):
        response = await async_client.get("/thread/thread_001", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["thread"]["thread_name"] == "Test Thread"

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, async_client, populated_db, auth_headers):
        response = await async_client.get("/thread/nonexistent", headers=auth_headers)
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_get_all_threads(self, async_client, populated_db, auth_headers):
        response = await async_client.get("/thread/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "thread_001" in data["threads"]


@pytest.mark.integration
class TestUpdateThread:
    @pytest.mark.asyncio
    async def test_update_thread_success(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.put(
            "/thread/thread_001",
            json={"thread_name": "Renamed Thread"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["thread_name"] == "Renamed Thread"

    @pytest.mark.asyncio
    async def test_update_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.put(
            "/thread/nope",
            json={"thread_name": "X"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data


@pytest.mark.integration
class TestDeleteThread:
    @pytest.mark.asyncio
    async def test_delete_thread_success(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete("/thread/thread_001", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete("/thread/nope", headers=auth_headers)
        data = response.json()
        assert "error" in data


@pytest.mark.integration
class TestDeleteDocument:
    @pytest.mark.asyncio
    @patch("app.routes.thread.delete_document_from_chroma", new_callable=AsyncMock)
    @patch("app.routes.thread.rebuild_bm25_after_deletion")
    async def test_delete_document_success(
        self, mock_bm25, mock_chroma, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete(
            "/thread/thread_001/document/doc_001", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_document_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete(
            "/thread/nope/document/doc_001", headers=auth_headers
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_delete_document_doc_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete(
            "/thread/thread_001/document/nonexistent", headers=auth_headers
        )
        data = response.json()
        assert "error" in data


@pytest.mark.integration
class TestDeleteChat:
    @pytest.mark.asyncio
    async def test_delete_chat_success(self, async_client, populated_db, auth_headers):
        response = await async_client.delete(
            "/thread/thread_001/chats/0", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["deleted_index"] == 0

    @pytest.mark.asyncio
    async def test_delete_chat_invalid_index(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete(
            "/thread/thread_001/chats/999", headers=auth_headers
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_clear_all_chats(self, async_client, populated_db, auth_headers):
        response = await async_client.delete(
            "/thread/thread_001/chats", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["chats"] == []

    @pytest.mark.asyncio
    async def test_clear_chats_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete("/thread/nope/chats", headers=auth_headers)
        data = response.json()
        assert "error" in data


@pytest.mark.integration
class TestInstructions:
    @pytest.mark.asyncio
    async def test_get_instructions_empty(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.get(
            "/thread/thread_001/instructions", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["instructions"] == []

    @pytest.mark.asyncio
    async def test_add_instruction(self, async_client, populated_db, auth_headers):
        response = await async_client.post(
            "/thread/thread_001/instructions",
            json={"text": "Always respond in bullet points"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["instruction"]["text"] == "Always respond in bullet points"
        assert data["instruction"]["selected"] is True

    @pytest.mark.asyncio
    async def test_add_instruction_thread_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            "/thread/nope/instructions",
            json={"text": "Test"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_update_instruction(self, async_client, populated_db, auth_headers):
        # Add first
        add_resp = await async_client.post(
            "/thread/thread_001/instructions",
            json={"text": "Original text"},
            headers=auth_headers,
        )
        inst_id = add_resp.json()["instruction"]["id"]

        # Update
        response = await async_client.put(
            f"/thread/thread_001/instructions/{inst_id}",
            json={"text": "Updated text", "selected": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["instruction"]["text"] == "Updated text"
        assert data["instruction"]["selected"] is False

    @pytest.mark.asyncio
    async def test_update_instruction_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.put(
            "/thread/thread_001/instructions/missing_id",
            json={"text": "X"},
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_delete_instruction(self, async_client, populated_db, auth_headers):
        # Add first
        add_resp = await async_client.post(
            "/thread/thread_001/instructions",
            json={"text": "Delete me"},
            headers=auth_headers,
        )
        inst_id = add_resp.json()["instruction"]["id"]

        # Delete
        response = await async_client.delete(
            f"/thread/thread_001/instructions/{inst_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_instruction_not_found(
        self, async_client, populated_db, auth_headers
    ):
        response = await async_client.delete(
            "/thread/thread_001/instructions/missing",
            headers=auth_headers,
        )
        data = response.json()
        assert "error" in data
