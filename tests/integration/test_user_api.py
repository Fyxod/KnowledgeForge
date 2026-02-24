"""
Integration tests for /user API endpoints — signup, login, get user.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch


@pytest.mark.integration
class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, async_client, patched_db):
        response = await async_client.post(
            "/user/",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "securepass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
        assert "password" not in data["user"]

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, async_client, patched_db):
        # Create first user
        await async_client.post(
            "/user/",
            json={
                "name": "User One",
                "email": "dupe@example.com",
                "password": "pass123",
            },
        )
        # Try duplicate
        response = await async_client.post(
            "/user/",
            json={
                "name": "User Two",
                "email": "dupe@example.com",
                "password": "pass456",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, async_client, patched_db):
        response = await async_client.post(
            "/user/",
            json={
                "name": "Bad Email",
                "email": "not-an-email",
                "password": "pass123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_missing_password(self, async_client, patched_db):
        response = await async_client.post(
            "/user/",
            json={
                "name": "No Pass",
                "email": "nopass@example.com",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_empty_name(self, async_client, patched_db):
        response = await async_client.post(
            "/user/",
            json={
                "name": "",
                "email": "empty@example.com",
                "password": "pass123",
            },
        )
        # Should still work (empty name allowed by model)
        assert response.status_code == 200


@pytest.mark.integration
class TestLoginUser:
    @pytest.mark.asyncio
    async def test_login_success(self, async_client, patched_db):
        # Create user first
        await async_client.post(
            "/user/",
            json={
                "name": "Login User",
                "email": "login@example.com",
                "password": "correctpass",
            },
        )
        # Login
        response = await async_client.post(
            "/user/login",
            json={
                "email": "login@example.com",
                "password": "correctpass",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client, patched_db):
        await async_client.post(
            "/user/",
            json={
                "name": "Login User",
                "email": "loginwrong@example.com",
                "password": "correctpass",
            },
        )
        response = await async_client.post(
            "/user/login",
            json={
                "email": "loginwrong@example.com",
                "password": "wrongpass",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, async_client, patched_db):
        response = await async_client.post(
            "/user/login",
            json={
                "email": "ghost@example.com",
                "password": "pass",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, async_client, patched_db):
        response = await async_client.post(
            "/user/login",
            json={
                "email": "bademail",
                "password": "pass",
            },
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self, async_client, populated_db, auth_headers):
        response = await async_client.get("/user/user_test_123", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user"]["userId"] == "user_test_123"

    @pytest.mark.asyncio
    async def test_get_user_no_auth(self, async_client, patched_db):
        response = await async_client.get("/user/user_test_123")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_wrong_user(self, async_client, populated_db, auth_headers):
        """User can only access their own profile."""
        response = await async_client.get("/user/other_user_id", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, async_client, patched_db, auth_headers):
        response = await async_client.get("/user/user_test_123", headers=auth_headers)
        assert response.status_code == 404
