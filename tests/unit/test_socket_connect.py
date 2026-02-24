"""
Unit tests for app.socket_handler — connect/disconnect event handlers.
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.unit
class TestConnectHandler:
    @pytest.mark.asyncio
    @patch("app.socket_handler.sio", new_callable=MagicMock)
    async def test_connect_adds_to_active(self, mock_sio):
        from app.socket_handler import connect, active_connections, heartbeat_tasks

        mock_sio.emit = AsyncMock()
        sid = "connect_test_sid"
        active_connections.discard(sid)

        try:
            await connect(sid, {})
            assert sid in active_connections
            assert sid in heartbeat_tasks
            # Clean up the heartbeat task
            heartbeat_tasks[sid].cancel()
            try:
                await heartbeat_tasks[sid]
            except asyncio.CancelledError:
                pass
        finally:
            active_connections.discard(sid)
            heartbeat_tasks.pop(sid, None)

    @pytest.mark.asyncio
    @patch("app.socket_handler.sio", new_callable=MagicMock)
    async def test_connect_with_auth(self, mock_sio):
        from app.socket_handler import connect, active_connections, heartbeat_tasks

        mock_sio.emit = AsyncMock()
        sid = "auth_connect_sid"
        active_connections.discard(sid)

        try:
            await connect(sid, {}, auth={"token": "abc123"})
            assert sid in active_connections
        finally:
            task = heartbeat_tasks.pop(sid, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            active_connections.discard(sid)


@pytest.mark.unit
class TestDisconnectHandler:
    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active(self):
        from app.socket_handler import disconnect, active_connections, heartbeat_tasks

        sid = "disconnect_test_sid"
        active_connections.add(sid)

        # Create a dummy heartbeat task
        async def dummy():
            try:
                while True:
                    await asyncio.sleep(1000)
            except asyncio.CancelledError:
                pass

        heartbeat_tasks[sid] = asyncio.create_task(dummy())

        await disconnect(sid)

        assert sid not in active_connections
        assert sid not in heartbeat_tasks

    @pytest.mark.asyncio
    async def test_disconnect_without_heartbeat(self):
        from app.socket_handler import disconnect, active_connections, heartbeat_tasks

        sid = "no_heartbeat_sid"
        active_connections.add(sid)

        await disconnect(sid)

        assert sid not in active_connections
        assert sid not in heartbeat_tasks
