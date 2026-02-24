"""
Unit tests for app.middlewares.auth — JWT authentication middleware.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import jwt as pyjwt


SECRET_KEY = "test-secret-key-for-jwt"


@pytest.mark.unit
class TestNormalizePath:
    def test_strips_trailing_slash(self):
        from app.middlewares.auth import normalize_path

        assert normalize_path("/api/test/") == "/api/test"

    def test_no_trailing_slash(self):
        from app.middlewares.auth import normalize_path

        assert normalize_path("/api/test") == "/api/test"

    def test_root_path(self):
        from app.middlewares.auth import normalize_path

        # "/" is preserved as-is (special case)
        assert normalize_path("/") == "/"

    def test_empty_string(self):
        from app.middlewares.auth import normalize_path

        assert normalize_path("") == ""

    def test_multiple_slashes(self):
        from app.middlewares.auth import normalize_path

        result = normalize_path("/api/test///")
        # Should strip the final slash
        assert not result.endswith("/") or result == ""


@pytest.mark.unit
class TestJWTTokenGeneration:
    """Tests for JWT token creation and validation (used across the app)."""

    def test_valid_token_decodes(self):
        payload = {
            "userId": "u1",
            "name": "Test",
            "email": "test@test.com",
            "is_active": True,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        }
        token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
        decoded = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        assert decoded["userId"] == "u1"

    def test_expired_token_raises(self):
        payload = {
            "userId": "u1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
        with pytest.raises(pyjwt.ExpiredSignatureError):
            pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])

    def test_invalid_secret_raises(self):
        payload = {
            "userId": "u1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
        with pytest.raises(pyjwt.InvalidSignatureError):
            pyjwt.decode(token, "wrong-secret", algorithms=["HS256"])

    def test_malformed_token_raises(self):
        with pytest.raises(pyjwt.DecodeError):
            pyjwt.decode("not.a.token", SECRET_KEY, algorithms=["HS256"])


@pytest.mark.unit
class TestAuthPaths:
    def test_auth_paths_is_list(self):
        from app.middlewares.auth_paths import auth_paths

        assert isinstance(auth_paths, list)

    def test_contains_expected_paths(self):
        from app.middlewares.auth_paths import auth_paths

        expected = ["/user", "/upload", "/query", "/thread", "/export"]
        for path in expected:
            assert path in auth_paths

    def test_health_not_in_auth_paths(self):
        from app.middlewares.auth_paths import auth_paths

        assert "/health" not in auth_paths
