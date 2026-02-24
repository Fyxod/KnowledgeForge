"""
Unit tests for app.socket_handler — Socket.IO connection management.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.unit
class TestIsClientConnected:
    def test_connected_client(self):
        from app.socket_handler import is_client_connected, active_connections

        active_connections.add("test_sid")
        try:
            assert is_client_connected("test_sid") is True
        finally:
            active_connections.discard("test_sid")

    def test_disconnected_client(self):
        from app.socket_handler import is_client_connected, active_connections

        active_connections.discard("nonexistent_sid")
        assert is_client_connected("nonexistent_sid") is False

    def test_after_disconnect(self):
        from app.socket_handler import is_client_connected, active_connections

        active_connections.add("temp_sid")
        active_connections.discard("temp_sid")
        assert is_client_connected("temp_sid") is False


@pytest.mark.unit
class TestActiveConnections:
    def test_is_set(self):
        from app.socket_handler import active_connections

        assert isinstance(active_connections, set)

    def test_add_and_remove(self):
        from app.socket_handler import active_connections

        sid = "test_sid_unit"
        active_connections.add(sid)
        assert sid in active_connections
        active_connections.discard(sid)
        assert sid not in active_connections
