"""
Integration tests for the Health API endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.integration
class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, async_client):
        response = await async_client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, async_client):
        """Health endpoint should work without authentication."""
        response = await async_client.get("/health/")
        assert response.status_code == 200
