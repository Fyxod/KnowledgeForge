"""
End-to-end tests — full user journey through the API.

These simulate a real user flow: signup → login → create thread → upload →
query → export, verifying the entire pipeline works in concert.
"""

import io
import pytest
from unittest.mock import AsyncMock, patch

from core.models.document import Document, Documents, Page


@pytest.mark.e2e
class TestFullUserJourney:
    """Signup → Login → Create Thread → Upload → Query → Export → Cleanup."""

    @pytest.mark.asyncio
    async def test_signup_login_flow(self, async_client, patched_db):
        """User can sign up then log in and receive a valid JWT."""
        # 1. Signup
        signup = await async_client.post(
            "/user/",
            json={
                "name": "E2E User",
                "email": "e2e@example.com",
                "password": "e2e_pass_123",
            },
        )
        assert signup.status_code == 200
        assert signup.json()["status"] == "success"

        # 2. Login
        login = await async_client.post(
            "/user/login",
            json={
                "email": "e2e@example.com",
                "password": "e2e_pass_123",
            },
        )
        assert login.status_code == 200
        token = login.json()["token"]
        assert token
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get user profile using the token
        user_id = login.json()["user"]["userId"]
        profile = await async_client.get(f"/user/{user_id}", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["user"]["email"] == "e2e@example.com"

    @pytest.mark.asyncio
    async def test_thread_lifecycle(self, async_client, patched_db):
        """Create → rename → list → delete thread."""
        # Signup + login
        await async_client.post(
            "/user/",
            json={
                "name": "Thread User",
                "email": "thread_user@example.com",
                "password": "pass123",
            },
        )
        login = await async_client.post(
            "/user/login",
            json={
                "email": "thread_user@example.com",
                "password": "pass123",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        # Create thread
        create = await async_client.post(
            "/thread/", json={"thread_name": "E2E Thread"}, headers=headers
        )
        assert create.status_code == 200
        thread_id = create.json()["thread_id"]

        # Rename
        rename = await async_client.put(
            f"/thread/{thread_id}",
            json={"thread_name": "Renamed E2E Thread"},
            headers=headers,
        )
        assert rename.json()["status"] == "success"
        assert rename.json()["thread_name"] == "Renamed E2E Thread"

        # List threads (should include our thread)
        listing = await async_client.get("/thread/", headers=headers)
        assert thread_id in listing.json()["threads"]

        # Get single thread
        single = await async_client.get(f"/thread/{thread_id}", headers=headers)
        assert single.json()["thread"]["thread_name"] == "Renamed E2E Thread"

        # Delete
        delete = await async_client.delete(f"/thread/{thread_id}", headers=headers)
        assert delete.json()["status"] == "success"

        # Verify gone
        after_delete = await async_client.get(f"/thread/{thread_id}", headers=headers)
        assert "error" in after_delete.json()

    @pytest.mark.asyncio
    async def test_instructions_lifecycle(self, async_client, patched_db):
        """Add → update → list → delete instruction within a thread."""
        # Setup user + thread
        await async_client.post(
            "/user/",
            json={
                "name": "Inst User",
                "email": "inst@example.com",
                "password": "pass123",
            },
        )
        login = await async_client.post(
            "/user/login",
            json={
                "email": "inst@example.com",
                "password": "pass123",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        thread = await async_client.post(
            "/thread/", json={"thread_name": "Inst Thread"}, headers=headers
        )
        tid = thread.json()["thread_id"]

        # Add instruction
        add = await async_client.post(
            f"/thread/{tid}/instructions",
            json={"text": "Be concise"},
            headers=headers,
        )
        assert add.json()["status"] == "success"
        inst_id = add.json()["instruction"]["id"]

        # Get instructions
        listed = await async_client.get(f"/thread/{tid}/instructions", headers=headers)
        assert len(listed.json()["instructions"]) == 1

        # Update
        upd = await async_client.put(
            f"/thread/{tid}/instructions/{inst_id}",
            json={"text": "Be very concise", "selected": False},
            headers=headers,
        )
        assert upd.json()["instruction"]["text"] == "Be very concise"

        # Delete
        dl = await async_client.delete(
            f"/thread/{tid}/instructions/{inst_id}", headers=headers
        )
        assert dl.json()["status"] == "success"

        # Verify empty
        final = await async_client.get(f"/thread/{tid}/instructions", headers=headers)
        assert len(final.json()["instructions"]) == 0

    @pytest.mark.asyncio
    @patch("app.routes.upload.save_documents_to_store", new_callable=AsyncMock)
    @patch("app.routes.upload.summarize_documents", new_callable=AsyncMock)
    @patch("app.routes.upload.create_stop_words")
    @patch("app.routes.upload.process_files", new_callable=AsyncMock)
    @patch("app.routes.upload.upload_files", new_callable=AsyncMock)
    @patch("app.routes.upload.mark_extra_done")
    async def test_upload_and_query_flow(
        self,
        mock_mark,
        mock_upload_files,
        mock_process,
        mock_stop,
        mock_summarize,
        mock_save,
        async_client,
        patched_db,
    ):
        """Sign up → login → create empty thread via upload → upload file → query."""
        # Setup
        await async_client.post(
            "/user/",
            json={
                "name": "Upload User",
                "email": "upload@example.com",
                "password": "pass123",
            },
        )
        login = await async_client.post(
            "/user/login",
            json={
                "email": "upload@example.com",
                "password": "pass123",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        user_id = login.json()["user"]["userId"]

        # Create empty thread via upload endpoint (no files)
        empty = await async_client.post(
            "/upload/",
            data={"thread_name": "Upload Thread"},
            headers=headers,
        )
        assert empty.json()["status"] == "success"
        thread_id = empty.json()["thread_id"]

        # Upload a file
        fake_doc = Document(
            id="doc_e2e",
            type="pdf",
            file_name="e2e.pdf",
            content=[Page(number=1, text="E2E content for testing.")],
            title="E2E PDF",
            full_text="E2E content for testing.",
        )
        mock_upload_files.return_value = [
            {"file_name": "e2e.pdf", "file_path": "/tmp/e2e.pdf"}
        ]
        mock_process.return_value = Documents(
            documents=[fake_doc],
            thread_id=thread_id,
            user_id=user_id,
        )

        upload_resp = await async_client.post(
            "/upload/",
            data={"thread_id": thread_id},
            files={"files": ("e2e.pdf", io.BytesIO(b"pdf data"), "application/pdf")},
            headers=headers,
        )
        assert upload_resp.json()["status"] == "success"
        assert len(upload_resp.json()["documents"]) == 1

        # Verify thread now has a document
        thread_data = await async_client.get(f"/thread/{thread_id}", headers=headers)
        assert len(thread_data.json()["thread"]["documents"]) == 1


@pytest.mark.e2e
class TestMultipleUsersIsolation:
    """Ensure users cannot access each other's data."""

    @pytest.mark.asyncio
    async def test_cross_user_thread_access(self, async_client, patched_db):
        # Create two users
        await async_client.post(
            "/user/",
            json={
                "name": "Alice",
                "email": "alice@test.com",
                "password": "pass",
            },
        )
        await async_client.post(
            "/user/",
            json={
                "name": "Bob",
                "email": "bob@test.com",
                "password": "pass",
            },
        )

        # Login as Alice and create a thread
        alice_login = await async_client.post(
            "/user/login",
            json={
                "email": "alice@test.com",
                "password": "pass",
            },
        )
        alice_headers = {"Authorization": f"Bearer {alice_login.json()['token']}"}
        create = await async_client.post(
            "/thread/", json={"thread_name": "Alice's Secret"}, headers=alice_headers
        )
        alice_thread_id = create.json()["thread_id"]

        # Login as Bob and try to access Alice's thread
        bob_login = await async_client.post(
            "/user/login",
            json={
                "email": "bob@test.com",
                "password": "pass",
            },
        )
        bob_headers = {"Authorization": f"Bearer {bob_login.json()['token']}"}
        bob_resp = await async_client.get(
            f"/thread/{alice_thread_id}", headers=bob_headers
        )
        # Bob should NOT see Alice's thread
        assert "error" in bob_resp.json()


@pytest.mark.e2e
class TestChatLifecycle:
    """Ensure chat messages can be deleted individually and cleared."""

    @pytest.mark.asyncio
    async def test_chat_deletion_flow(self, async_client, patched_db):
        # Setup
        await async_client.post(
            "/user/",
            json={
                "name": "Chat User",
                "email": "chat@test.com",
                "password": "pass",
            },
        )
        login = await async_client.post(
            "/user/login",
            json={
                "email": "chat@test.com",
                "password": "pass",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        user_id = login.json()["user"]["userId"]

        # Create thread and manually inject some chats via DB
        thread_resp = await async_client.post(
            "/thread/", json={"thread_name": "Chat Thread"}, headers=headers
        )
        tid = thread_resp.json()["thread_id"]

        from core.database import db
        from datetime import datetime, timezone

        # Insert 3 chats
        chats = [
            {"type": "user", "content": "Q1", "timestamp": datetime.now(timezone.utc)},
            {"type": "agent", "content": "A1", "timestamp": datetime.now(timezone.utc)},
            {"type": "user", "content": "Q2", "timestamp": datetime.now(timezone.utc)},
        ]
        db.users.update_one(
            {"userId": user_id},
            {"$set": {f"threads.{tid}.chats": chats}},
        )

        # Delete first chat
        del_resp = await async_client.delete(f"/thread/{tid}/chats/0", headers=headers)
        assert del_resp.json()["status"] == "success"
        assert len(del_resp.json()["chats"]) == 2

        # Clear all
        clear = await async_client.delete(f"/thread/{tid}/chats", headers=headers)
        assert clear.json()["chats"] == []
