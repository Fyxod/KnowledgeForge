import socketio
import asyncio

active_connections = set()
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_timeout=400,  # 5 minutes timeout
    ping_interval=20,  # keep sending ping every 20s
)

heartbeat_tasks = {}


@sio.event
async def connect(sid, environ):
    active_connections.add(sid)

    async def send_heartbeat():
        try:
            while True:
                await sio.emit("heartbeat", {"status": "processing..."}, to=sid)
                await asyncio.sleep(20)
        except asyncio.CancelledError:
            pass

    heartbeat_tasks[sid] = asyncio.create_task(send_heartbeat())


@sio.event
async def disconnect(sid):
    active_connections.discard(sid)
    task = heartbeat_tasks.pop(sid, None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def is_client_connected(sid):
    """Check if a client is connected."""
    return sid in active_connections
