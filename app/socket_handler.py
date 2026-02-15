"""
Socket.IO server with streaming query support.

Events handled
--------------
* ``connect`` / ``disconnect`` – lifecycle with heartbeat
* ``query_stream``  – run the full agent pipeline and stream the final answer
* ``reset_session`` – clear KV cache / history for a thread
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone

import jwt
import socketio
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from core.config import Settings
from core.constants import (
    CHUNK_COUNT,
    GPU_QUERY_LLM,
    GPU_QUERY_LLM2,
    PORT1,
    INTERNAL,
    EXTERNAL,
    SWITCHES,
)
from core.database import db
from core.embeddings.retriever import get_user_retriever
from core.llm.providers.registry import get_gemini_provider, get_provider
from core.llm.session_manager import session_manager
from core.llm.prompts.streaming_prompt import (
    build_streaming_prompt,
    build_streaming_combination_prompt,
)
from core.models.user import UserJwtPayload

from agent.decomposition import decomposition_node
from core.llm.outputs import DecompositionLLMOutput
from agent.tools.search import search_tavily as search_tool
from core.services.sqlite_manager import SQLiteManager
from agent.tools.sql_query import get_sql_schema
from agent.graph_helpers import get_recent_history

from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

# ── Socket.IO server ────────────────────────────────────────────────
active_connections: set[str] = set()
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_timeout=400,
    ping_interval=20,
)

heartbeat_tasks: dict[str, asyncio.Task] = {}
_sid_users: dict[str, UserJwtPayload] = {}


# ── Auth helper ─────────────────────────────────────────────────────
def _decode_token(token: str) -> UserJwtPayload:
    secret = Settings().SECRET_KEY
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return UserJwtPayload(**payload)


# ── Lifecycle ───────────────────────────────────────────────────────
@sio.event
async def connect(sid, environ, auth=None):
    logger.info(f"[WebSocket] Client connecting: {sid}")
    active_connections.add(sid)

    # Authenticate if token provided at connect
    if auth and isinstance(auth, dict):
        token = auth.get("token", "")
        if token:
            try:
                _sid_users[sid] = _decode_token(token)
                logger.info(f"[WebSocket] Authenticated user {_sid_users[sid].userId}")
            except Exception as exc:
                logger.warning(f"[WebSocket] Auth failed for {sid}: {exc}")

    async def send_heartbeat():
        try:
            while True:
                await sio.emit("heartbeat", {"status": "processing..."}, to=sid)
                await asyncio.sleep(20)
        except asyncio.CancelledError:
            pass

    heartbeat_tasks[sid] = asyncio.create_task(send_heartbeat())
    logger.info(f"[WebSocket] Client {sid} connected successfully")


@sio.event
async def disconnect(sid):
    logger.info(f"[WebSocket] Client disconnecting: {sid}")
    active_connections.discard(sid)
    _sid_users.pop(sid, None)
    task = heartbeat_tasks.pop(sid, None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info(f"[WebSocket] Client {sid} disconnected")


def is_client_connected(sid):
    """Check if a client is connected."""
    return sid in active_connections


# ── Streaming query event ───────────────────────────────────────────
@sio.event
async def query_stream(sid, data):
    """Handle a streaming query request.

    Payload::

        {
            "thread_id": "abc123",
            "question": "What is …?",
            "mode": "Internal" | "External",
            "use_self_knowledge": false,
            "token": "jwt-token"       // optional if already authenticated
        }

    Emits:
        stream_start  → { thread_id }
        stream_status → { status }        (progress updates)
        stream_token  → { token }         (individual tokens)
        stream_end    → { thread_id, answer, sources, timing }
        stream_error  → { error }
    """
    start_time = time.time()

    # ── Auth ─────────────────────────────────────────────────────
    user_payload = _sid_users.get(sid)
    if not user_payload:
        token = data.get("token", "")
        if token:
            try:
                user_payload = _decode_token(token)
                _sid_users[sid] = user_payload
            except Exception as exc:
                await sio.emit(
                    "stream_error",
                    {"error": f"Authentication failed: {exc}"},
                    to=sid,
                )
                return
        else:
            await sio.emit("stream_error", {"error": "Not authenticated"}, to=sid)
            return

    user_id = user_payload.userId
    thread_id = data.get("thread_id", "")
    question = data.get("question", "").strip()
    mode = data.get("mode", EXTERNAL)
    use_self_knowledge = data.get("use_self_knowledge", False)

    if not thread_id or not question:
        await sio.emit(
            "stream_error",
            {"error": "thread_id and question are required"},
            to=sid,
        )
        return

    session_id = session_manager.make_session_id(user_id, thread_id)
    session_manager.register(session_id)

    logger.info(
        f"[Stream] query from {user_id} | thread={thread_id} | "
        f"mode={mode} | q={question[:80]}…"
    )

    try:
        await sio.emit("stream_start", {"thread_id": thread_id}, to=sid)

        # ── Load user & thread ───────────────────────────────────
        user_doc = db.users.find_one({"userId": user_id}, {"_id": 0, "password": 0})
        if not user_doc:
            await sio.emit("stream_error", {"error": "User not found"}, to=sid)
            return

        thread = user_doc.get("threads", {}).get(thread_id)
        if not thread:
            await sio.emit("stream_error", {"error": "Thread not found"}, to=sid)
            return

        # ── Build message history ────────────────────────────────
        messages = []
        for msg in thread.get("chats", []):
            if msg["type"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "agent":
                messages.append(AIMessage(content=msg["content"]))

        # ── Spreadsheet check ────────────────────────────────────
        has_spreadsheet = SQLiteManager.has_spreadsheet_data(user_id, thread_id)
        spreadsheet_schema = None
        if has_spreadsheet:
            spreadsheet_schema = get_sql_schema(user_id, thread_id)

        # ── Decomposition ────────────────────────────────────────
        await sio.emit("stream_status", {"status": "Analysing query…"}, to=sid)

        if SWITCHES["DECOMPOSITION"]:
            decomposition_result: DecompositionLLMOutput = await decomposition_node(
                question,
                messages,
                has_spreadsheet_data=has_spreadsheet,
                spreadsheet_schema=spreadsheet_schema,
            )
        else:
            decomposition_result = DecompositionLLMOutput(
                requires_decomposition=False,
                resolved_query=question,
                sub_queries=[],
            )

        decomposed = decomposition_result.requires_decomposition
        resolved_query = decomposition_result.resolved_query or question

        # ── Retrieval ────────────────────────────────────────────
        await sio.emit("stream_status", {"status": "Retrieving documents…"}, to=sid)
        doc_retriever = get_user_retriever(user_id, thread_id, k=CHUNK_COUNT)
        retrieved_docs = await doc_retriever.ainvoke(resolved_query)
        chunks = [
            {
                "document_id": (doc.metadata or {}).get("document_id", ""),
                "title": (doc.metadata or {}).get("title", "Unknown"),
                "page_no": (doc.metadata or {}).get("page_no", 1),
                "content": doc.page_content,
            }
            for doc in retrieved_docs
        ]

        # ── Web search (External mode) ──────────────────────────
        initial_search_answer = ""
        initial_search_results: list = []
        all_favicons: list = []

        if mode == EXTERNAL:
            await sio.emit("stream_status", {"status": "Searching the web…"}, to=sid)
            try:
                sr = await search_tool(resolved_query)
                initial_search_answer = sr.get("answer", "")
                initial_search_results = sr.get("results", [])
                all_favicons = [
                    {
                        "favicon": r.get("favicon"),
                        "url": r.get("url"),
                        "title": r.get("title"),
                    }
                    for r in initial_search_results
                ]
            except Exception as exc:
                logger.warning(f"[Stream] Web search failed: {exc}")

        # ──────────────────────────────────────────────────────────
        # Helper: stream tokens from a provider with Gemini fallback
        # ──────────────────────────────────────────────────────────
        async def _stream_with_fallback(prompt_text: str) -> str:
            parts: list[str] = []
            # Try GPU_QUERY_LLM first, then GPU_QUERY_LLM2, then Gemini
            primary_port = GPU_QUERY_LLM.port
            fallback_port = GPU_QUERY_LLM2.port
            provider = get_provider(primary_port)
            try:
                async for tok in provider.stream(prompt_text, session_id):
                    if not is_client_connected(sid):
                        logger.warning("[Stream] Client disconnected during streaming")
                        return "".join(parts)
                    parts.append(tok)
                    await sio.emit("stream_token", {"token": tok}, to=sid)
            except Exception as exc:
                logger.error(
                    f"[Stream] Primary provider (port {primary_port}) failed: {exc}"
                )
                # Try fallback port
                parts.clear()
                try:
                    fallback_provider = get_provider(fallback_port)
                    logger.info(
                        f"[Stream] Trying fallback provider (port {fallback_port})"
                    )
                    async for tok in fallback_provider.stream(prompt_text, session_id):
                        if not is_client_connected(sid):
                            return "".join(parts)
                        parts.append(tok)
                        await sio.emit("stream_token", {"token": tok}, to=sid)
                except Exception as exc2:
                    logger.error(f"[Stream] Fallback provider also failed: {exc2}")
                    gemini = get_gemini_provider()
                    if gemini:
                        logger.info("[Stream] Falling back to Gemini streaming")
                        async for tok in gemini.stream(prompt_text, session_id):
                            if not is_client_connected(sid):
                                return "".join(parts)
                            parts.append(tok)
                            await sio.emit("stream_token", {"token": tok}, to=sid)
                    else:
                        raise
            return "".join(parts)

        # ── Decomposed flow ──────────────────────────────────────
        if decomposed and decomposition_result.sub_queries:
            await sio.emit(
                "stream_status",
                {
                    "status": (
                        f"Decomposed into "
                        f"{len(decomposition_result.sub_queries)} sub-queries…"
                    )
                },
                to=sid,
            )

            from agent.builder import Agent, AgentState

            sub_results = []
            for idx, sq in enumerate(decomposition_result.sub_queries):
                if not is_client_connected(sid):
                    return
                await sio.emit(
                    "stream_status",
                    {"status": f"Processing sub-query {idx + 1}…"},
                    to=sid,
                )

                sq_answer = ""
                sq_results: list = []
                if mode == EXTERNAL:
                    try:
                        sr = await search_tool(sq)
                        sq_answer = sr.get("answer", "")
                        sq_results = sr.get("results", [])
                    except Exception:
                        pass

                state = await Agent.ainvoke(
                    AgentState(
                        user_id=user_id,
                        thread_id=thread_id,
                        query=sq,
                        resolved_query=resolved_query,
                        original_query=question,
                        messages=[],
                        web_search=False,
                        llm=GPU_QUERY_LLM,
                        initial_search_answer=sq_answer,
                        initial_search_results=sq_results,
                        mode=mode,
                        use_self_knowledge=use_self_knowledge,
                        has_spreadsheet_data=has_spreadsheet,
                        spreadsheet_schema=spreadsheet_schema,
                    )
                )
                state = AgentState(**state)
                sub_results.append({"sub_query": sq, "sub_answer": state.answer})

            await sio.emit("stream_status", {"status": "Combining answers…"}, to=sid)
            combo_prompt = build_streaming_combination_prompt(
                resolved_query, sub_results
            )
            answer = await _stream_with_fallback(combo_prompt)

        # ── Non-decomposed flow ──────────────────────────────────
        else:
            await sio.emit(
                "stream_status",
                {"status": "Generating answer…"},
                to=sid,
            )

            recent = get_recent_history(messages, turns=5)
            prompt = build_streaming_prompt(
                messages=recent,
                chunks=chunks,
                question=resolved_query,
                mode=mode,
                initial_search_answer=initial_search_answer or None,
                initial_search_results=initial_search_results or None,
                use_self_knowledge=use_self_knowledge,
                spreadsheet_schema=spreadsheet_schema,
            )
            answer = await _stream_with_fallback(prompt)

        # ── Persist to DB ────────────────────────────────────────
        now = datetime.now(timezone.utc)
        docs_used: list[dict] = []
        web_used = all_favicons

        new_messages = [
            {"type": "user", "content": question, "timestamp": now},
            {
                "type": "agent",
                "content": answer,
                "timestamp": now,
                "sources": {
                    "documents_used": docs_used,
                    "web_used": web_used,
                },
            },
        ]
        db.users.update_one(
            {"userId": user_id},
            {
                "$push": {f"threads.{thread_id}.chats": {"$each": new_messages}},
                "$set": {f"threads.{thread_id}.updatedAt": now},
            },
        )

        # ── Log KV cache state ───────────────────────────────────
        from core.llm.providers.ollama import OllamaProvider

        for p in (GPU_QUERY_LLM.port, GPU_QUERY_LLM2.port):
            try:
                prov = get_provider(p)
                if isinstance(prov, OllamaProvider):
                    ctx_size = prov.get_context_size(session_id)
                    if ctx_size:
                        logger.info(
                            f"[KV Cache] Session {session_id} context size "
                            f"on port {p}: {ctx_size}"
                        )
            except Exception:
                pass

        total_time = time.time() - start_time
        logger.info(f"[Stream] Total query time: {total_time:.2f}s")

        await sio.emit(
            "stream_end",
            {
                "thread_id": thread_id,
                "answer": answer,
                "sources": {
                    "documents_used": docs_used,
                    "web_used": web_used,
                },
                "timing": {"total_seconds": round(total_time, 2)},
            },
            to=sid,
        )

    except Exception as exc:
        logger.error(f"[Stream] Error: {exc}")
        traceback.print_exc()
        await sio.emit("stream_error", {"error": str(exc)}, to=sid)


# ── Session reset event ─────────────────────────────────────────────
@sio.event
async def reset_session(sid, data):
    """Clear KV cache / conversation history for a thread.

    Payload::

        { "thread_id": "abc123" }
    """
    user_payload = _sid_users.get(sid)
    if not user_payload:
        await sio.emit(
            "session_reset_error",
            {"error": "Not authenticated"},
            to=sid,
        )
        return

    thread_id = data.get("thread_id", "")
    if not thread_id:
        await sio.emit(
            "session_reset_error",
            {"error": "thread_id is required"},
            to=sid,
        )
        return

    session_id = session_manager.make_session_id(user_payload.userId, thread_id)
    session_manager.reset(session_id)

    await sio.emit(
        "session_reset_ok",
        {"thread_id": thread_id, "message": "Session context cleared"},
        to=sid,
    )
    logger.info(f"[Stream] Session reset: {session_id}")
