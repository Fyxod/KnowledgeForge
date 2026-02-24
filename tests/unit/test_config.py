"""
Unit tests for core.config — Settings validation.
"""

import os

import pytest


@pytest.mark.unit
class TestSettings:
    def test_settings_loads(self):
        from core.config import settings

        assert settings is not None

    def test_required_fields_present(self):
        from core.config import settings

        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "SECRET_KEY")
        assert hasattr(settings, "DATABASE_NAME")
        assert hasattr(settings, "MAIN_MODEL")

    def test_mode_field(self):
        from core.config import settings

        assert settings.MODE in ("development", "production", "test")

    def test_remote_gpu_is_bool(self):
        from core.config import settings

        assert isinstance(settings.REMOTE_GPU, bool)

    def test_api_keys_present(self):
        from core.config import settings

        for i in range(1, 7):
            assert hasattr(settings, f"API_KEY_{i}")
