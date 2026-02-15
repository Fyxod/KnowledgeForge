"""
Google Gemini inference provider.

Unlike Ollama there is no KV cache to manage.  Instead we maintain a
per-session conversation history so the model receives prior context.
The history is trimmed automatically when it exceeds MAX_HISTORY_TURNS
to prevent unbounded memory growth.
"""

import asyncio
import logging
import threading
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from google import genai

from core.llm.providers.base import GenerateResult, InferenceProvider

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 20  # Maximum user+model pairs to keep


class GeminiProvider(InferenceProvider):
    """Inference provider for the Google Gemini API."""

    def __init__(
        self,
        api_keys: List[str],
        model: str = "gemini-2.5-flash",
    ):
        self.api_keys = [k for k in api_keys if k and k.strip()]
        if not self.api_keys:
            raise ValueError("At least one valid Gemini API key is required")
        self.model = model
        self._key_index = 0

        # Conversation history per session: list of {role, parts} dicts
        self._session_histories: Dict[str, List[Dict[str, Any]]] = {}
        logger.info(
            f"GeminiProvider initialised: model={model}, "
            f"{len(self.api_keys)} API key(s)"
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _next_client(self) -> genai.Client:
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index = (self._key_index + 1) % len(self.api_keys)
        return genai.Client(api_key=key)

    @staticmethod
    def _config() -> genai.types.GenerateContentConfig:
        return genai.types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=200000,
            response_mime_type="text/plain",
            safety_settings=[],
        )

    def _trim_history(self, session_id: str) -> None:
        history = self._session_histories.get(session_id, [])
        cap = MAX_HISTORY_TURNS * 2
        if len(history) > cap:
            self._session_histories[session_id] = history[-cap:]
            logger.info(
                f"[Gemini History] Trimmed session {session_id} "
                f"to last {MAX_HISTORY_TURNS} turns"
            )

    def _update_history(
        self, session_id: str, prompt: str, response_text: str
    ) -> None:
        if session_id not in self._session_histories:
            self._session_histories[session_id] = []
        self._session_histories[session_id].append(
            {"role": "user", "parts": [{"text": prompt}]}
        )
        self._session_histories[session_id].append(
            {"role": "model", "parts": [{"text": response_text}]}
        )
        self._trim_history(session_id)

    # ------------------------------------------------------------------
    # generate – full response
    # ------------------------------------------------------------------
    async def generate(self, prompt: str, session_id: str) -> GenerateResult:
        client = self._next_client()
        config = self._config()

        start = time.time()
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=config,
                ),
                timeout=120,
            )
        except asyncio.TimeoutError:
            logger.error("[Gemini] Request timed out (120 s)")
            raise

        text = ""
        try:
            text = response.text or str(response)
        except Exception:
            text = str(response)

        total_duration = time.time() - start

        # Extract token counts if available
        usage = getattr(response, "usage_metadata", None)
        p_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        c_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

        self._update_history(session_id, prompt, text)

        logger.info(
            f"[Gemini] Generated in {total_duration:.2f}s | "
            f"prompt_tokens={p_tokens} completion_tokens={c_tokens}"
        )

        return GenerateResult(
            text=text,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_duration=total_duration,
        )

    # ------------------------------------------------------------------
    # stream – token-by-token via a bridging queue
    # ------------------------------------------------------------------
    async def stream(
        self, prompt: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        client = self._next_client()
        config = self._config()

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        error_holder: List[Optional[Exception]] = [None]

        def _run_sync_stream() -> None:
            """Execute synchronous Gemini streaming in a worker thread."""
            try:
                response_iter = client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                for chunk in response_iter:
                    text = ""
                    try:
                        text = chunk.text or ""
                    except Exception:
                        text = ""
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as exc:
                error_holder[0] = exc
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        start = time.time()
        first_token_seen = False
        total_chunks = 0
        full_response_parts: List[str] = []

        thread = threading.Thread(target=_run_sync_stream, daemon=True)
        thread.start()

        try:
            while True:
                token = await queue.get()
                if token is None:
                    break

                if not first_token_seen:
                    ttft = time.time() - start
                    logger.info(
                        f"[Gemini Streaming] Time to first token: {ttft:.3f}s"
                    )
                    first_token_seen = True

                total_chunks += 1
                full_response_parts.append(token)
                yield token
        finally:
            thread.join(timeout=5.0)

        if error_holder[0]:
            logger.error(f"[Gemini Streaming] Error: {error_holder[0]}")
            raise error_holder[0]

        total_duration = time.time() - start
        complete_text = "".join(full_response_parts)
        self._update_history(session_id, prompt, complete_text)

        logger.info(
            f"[Gemini Streaming] Complete: {total_chunks} chunks "
            f"in {total_duration:.2f}s"
        )

    # ------------------------------------------------------------------
    # session management
    # ------------------------------------------------------------------
    def reset_session(self, session_id: str) -> None:
        removed = self._session_histories.pop(session_id, None)
        if removed:
            logger.info(
                f"[Gemini History] Cleared history for session {session_id} "
                f"(was {len(removed)} entries)"
            )
        else:
            logger.info(
                f"[Gemini History] No history to clear for session {session_id}"
            )
