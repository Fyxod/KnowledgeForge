"""
Root conftest.py — shared fixtures used across all test types.

Provides:
  - Mocked MongoDB (mongomock)
  - Mocked settings/env
  - FastAPI TestClient
  - Authenticated request helpers
  - Common test data builders
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import mongomock
import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Env setup BEFORE any app imports
# ---------------------------------------------------------------------------
os.environ.update(
    {
        "DATABASE_URL": "mongodb://localhost:27017/test_bedrock",
        "DATABASE_NAME": "test_bedrock",
        "SECRET_KEY": "test-secret-key-for-jwt",
        "MODE": "test",
        "API_KEY_1": "test-key-1",
        "API_KEY_2": "test-key-2",
        "API_KEY_3": "test-key-3",
        "API_KEY_4": "test-key-4",
        "API_KEY_5": "test-key-5",
        "API_KEY_6": "test-key-6",
        "OPENAI_API": "test-openai-key",
        "QUERY_URL": "http://localhost:11434",
        "VISION_URL": "http://localhost:11435",
        "MAIN_MODEL": "test-model",
        "REMOTE_GPU": "false",
        "USE_VISION_MODEL": "false",
        "LOCAL_BASE_URL": "http://localhost",
    }
)


# ---------------------------------------------------------------------------
# MongoDB fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def mock_mongo_client():
    """Provides a mongomock client with a clean test database."""
    client = mongomock.MongoClient()
    yield client
    client.close()


@pytest.fixture()
def mock_db(mock_mongo_client):
    """Provides a clean test database collection."""
    db = mock_mongo_client["test_bedrock"]
    yield db
    mock_mongo_client.drop_database("test_bedrock")


@pytest.fixture()
def patched_db(mock_db):
    """Patches core.database.db AND every module that directly imported it."""
    _targets = [
        "core.database.db",
        "app.routes.user.db",
        "app.routes.thread.db",
        "app.routes.query.db",
        "app.routes.upload.db",
        "app.routes.export.db",
        "app.routes.documents.db",
        "app.routes.extra.db",
        "app.routes.insights.db",
        "app.routes.strategic_analysis.db",
        "app.routes.strategic_roadmap.db",
        "app.routes.technical_analysis.db",
        "app.routes.technical_roadmap.db",
        "core.utils.extra_done_check.db",
        "core.studio_features.summarizer.db",
    ]
    patches = [patch(t, mock_db) for t in _targets]
    for p in patches:
        p.start()
    yield mock_db
    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# JWT / Auth helpers
# ---------------------------------------------------------------------------
@pytest.fixture()
def jwt_secret():
    return "test-secret-key-for-jwt"


@pytest.fixture()
def sample_user_payload():
    """Standard JWT payload for a test user."""
    return {
        "userId": "user_test_123",
        "name": "Test User",
        "email": "test@example.com",
        "is_active": True,
    }


@pytest.fixture()
def auth_token(sample_user_payload, jwt_secret):
    """Generates a valid JWT token for test requests."""
    import jwt as pyjwt
    from datetime import timedelta

    payload = {
        **sample_user_payload,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return pyjwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture()
def auth_headers(auth_token):
    """Returns headers dict with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# Sample data builders
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_thread_doc():
    """A minimal ThreadDocument dict as stored in MongoDB."""
    return {
        "docId": "doc_001",
        "title": "Test Document",
        "type": "pdf",
        "time_uploaded": datetime.now(timezone.utc),
        "file_name": "test_doc.pdf",
    }


@pytest.fixture()
def sample_chat_message():
    return {
        "type": "user",
        "content": "What is this document about?",
        "timestamp": datetime.now(timezone.utc),
    }


@pytest.fixture()
def sample_thread(sample_thread_doc, sample_chat_message):
    """A fully populated thread dict matching the MongoDB schema."""
    return {
        "thread_name": "Test Thread",
        "documents": [sample_thread_doc],
        "chats": [sample_chat_message],
        "instructions": [],
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "extra_done": False,
    }


@pytest.fixture()
def sample_user_in_db(sample_thread):
    """A complete user doc ready for MongoDB insertion."""
    return {
        "userId": "user_test_123",
        "name": "Test User",
        "email": "test@example.com",
        "password": "$2b$12$somehashed",
        "is_active": True,
        "threads": {"thread_001": sample_thread},
    }


@pytest.fixture()
def populated_db(patched_db, sample_user_in_db):
    """A patched DB with one user already inserted."""
    patched_db.users.insert_one(sample_user_in_db)
    return patched_db


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------
@pytest.fixture()
def mock_sio():
    """Mock Socket.IO server to prevent real socket operations."""
    mock = AsyncMock()
    mock.emit = AsyncMock()
    with patch("app.socket_handler.sio", mock):
        yield mock


@pytest.fixture()
async def async_client(patched_db, mock_sio):
    """
    Async HTTP client for FastAPI integration tests.
    Patches DB + socketio before importing the app.
    """
    # Lazy import so patches are in place
    from app.main import fastapi_app

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# LLM / external service mocks
# ---------------------------------------------------------------------------
@pytest.fixture()
def mock_invoke_llm():
    """Patches invoke_llm globally and returns the mock for assertion."""
    with patch("core.llm.client.invoke_llm", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture()
def mock_tavily():
    """Patches Tavily search tool."""
    with patch("agent.tools.search.search_tavily", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "answer": "Tavily answer",
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example.com",
                    "content": "Some content",
                }
            ],
        }
        yield mock


@pytest.fixture()
def mock_embeddings():
    """Patches the embedding function."""
    with patch("core.embeddings.embeddings.get_embedding_function") as mock:
        fake_embed = MagicMock()
        fake_embed.embed_documents.return_value = [[0.1] * 768]
        fake_embed.embed_query.return_value = [0.1] * 768
        mock.return_value = fake_embed
        yield mock


@pytest.fixture()
def mock_vectorstore():
    """Patches vectorstore operations."""
    with patch("core.embeddings.vectorstore.get_vectorstore") as mock:
        fake_vs = MagicMock()
        fake_vs.similarity_search.return_value = []
        fake_vs.add_documents.return_value = None
        mock.return_value = fake_vs
        yield mock


# ---------------------------------------------------------------------------
# Temp file helpers
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Creates a temporary data directory tree mimicking the app structure."""
    user_dir = tmp_path / "data" / "user_test_123" / "threads" / "thread_001"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "uploads").mkdir(exist_ok=True)
    (user_dir / "parsed").mkdir(exist_ok=True)
    return tmp_path
