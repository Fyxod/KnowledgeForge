"""
Integration tests for studio feature endpoints:
  - POST /insights, POST /insights/global
  - POST /strategic_analysis, POST /strategic_analysis/global
  - POST /strategic_roadmap, POST /strategic_roadmap/global
  - POST /technical_analysis, POST /technical_analysis/global
  - POST /technical_roadmap, POST /technical_roadmap/global

These all follow the same generate-or-poll pattern so tests are parameterised.
"""

import pytest
from unittest.mock import patch


# (endpoint, body_key_single, body_key_global)
STUDIO_FEATURES = [
    ("/insights", "insights", "insights"),
    ("/strategic_analysis", "strategic_analysis", "strategic_analysis"),
    ("/strategic_roadmap", "strategic_roadmap", "strategic_roadmap"),
    ("/technical_analysis", "technical_analysis", "technical_analysis"),
    ("/technical_roadmap", "technical_roadmap", "technical_roadmap"),
]


def _single_body(thread_id="thread_001", document_id="doc_001"):
    return {"thread_id": thread_id, "document_id": document_id}


def _global_body(thread_id="thread_001"):
    return {"thread_id": thread_id}


@pytest.mark.integration
class TestStudioFeaturesAuth:
    """Auth guard — every feature should reject unauthenticated requests."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_single_no_auth(self, endpoint, _a, _b, async_client, patched_db):
        response = await async_client.post(endpoint, json=_single_body())
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_global_no_auth(self, endpoint, _a, _b, async_client, patched_db):
        response = await async_client.post(f"{endpoint}/global", json=_global_body())
        assert response.status_code == 401


@pytest.mark.integration
class TestStudioFeaturesUserNotFound:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_single_user_not_found(
        self, endpoint, _a, _b, async_client, patched_db, auth_headers
    ):
        response = await async_client.post(
            endpoint, json=_single_body(), headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_global_user_not_found(
        self, endpoint, _a, _b, async_client, patched_db, auth_headers
    ):
        response = await async_client.post(
            f"{endpoint}/global", json=_global_body(), headers=auth_headers
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestStudioFeaturesThreadNotFound:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_single_thread_not_found(
        self, endpoint, _a, _b, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            endpoint,
            json=_single_body(thread_id="nonexistent"),
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_global_thread_not_found(
        self, endpoint, _a, _b, async_client, populated_db, auth_headers
    ):
        response = await async_client.post(
            f"{endpoint}/global",
            json=_global_body(thread_id="nonexistent"),
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestStudioFeaturesDocumentNotFound:
    """Single-document endpoints should return 404 when document isn't found."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,_a,_b", STUDIO_FEATURES)
    async def test_document_not_found(
        self, endpoint, _a, _b, async_client, populated_db, auth_headers
    ):
        # parsed dir doesn't exist on disk → document not found
        response = await async_client.post(
            endpoint,
            json=_single_body(document_id="nonexistent_doc"),
            headers=auth_headers,
        )
        assert response.status_code == 404
