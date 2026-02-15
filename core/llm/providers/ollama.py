"""
Ollama inference provider with KV cache support.

Uses Ollama's /api/generate endpoint directly (not LangChain)
to access the `context` field for KV caching.

KV caching behaviour:
- After each generation the returned `context` array is stored per session_id.
- On the next request the stored context is passed back, allowing Ollama to
  skip re-processing the previous conversation – dramatically reducing latency.
- reset_session() clears the stored context.
"""

import json
import logging
import re
import time
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from core.llm.providers.base import GenerateResult, InferenceProvider

logger = logging.getLogger(__name__)


class OllamaProvider(InferenceProvider):
    """Inference provider for Ollama (local or remote Ollama server)."""

    def __init__(self, base_url: str, model: str, port: int = 11434):
        self.base_url = f"{base_url}:{port}"
        self.model = model
        self.port = port

        # KV cache: session_id -> context token array
        self._session_contexts: Dict[str, List[int]] = {}

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)
        )
        logger.info(
            f"OllamaProvider initialised: model={model}, url={self.base_url}"
        )

    # ------------------------------------------------------------------
    # generate – full response, KV-cached
    # ------------------------------------------------------------------
    async def generate(self, prompt: str, session_id: str) -> GenerateResult:
        url = f"{self.base_url}/api/generate"
        context = self._session_contexts.get(session_id)

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if context:
            payload["context"] = context
            logger.info(
                f"[KV Cache] Reusing context for session {session_id} "
                f"(size: {len(context)})"
            )
        else:
            logger.info(
                f"[KV Cache] No cached context for session {session_id} (cold start)"
            )

        start = time.time()
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        total_duration = time.time() - start
        data = response.json()

        # Persist context for next call
        new_context = data.get("context", [])
        if new_context:
            self._session_contexts[session_id] = new_context
            logger.info(
                f"[KV Cache] Updated context for session {session_id} "
                f"(size: {len(new_context)})"
            )

        raw_text = data.get("response", "")
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        prompt_eval_ns = data.get("prompt_eval_duration", 0)
        ttft = prompt_eval_ns / 1e9 if prompt_eval_ns else 0.0

        logger.info(
            f"[Ollama] Generated in {total_duration:.2f}s | "
            f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} "
            f"ttft={ttft:.3f}s"
        )

        return GenerateResult(
            text=cleaned,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            time_to_first_token=ttft,
            total_duration=total_duration,
            context=new_context,
        )

    # ------------------------------------------------------------------
    # stream – token-by-token, KV-cached
    # ------------------------------------------------------------------
    async def stream(
        self, prompt: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/generate"
        context = self._session_contexts.get(session_id)

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        if context:
            payload["context"] = context
            logger.info(
                f"[KV Cache] Reusing context for session {session_id} "
                f"(size: {len(context)})"
            )

        start = time.time()
        first_token_seen = False
        total_tokens = 0

        async with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = data.get("response", "")
                if token:
                    # Strip thinking tags from individual tokens
                    token = re.sub(
                        r"<think>.*?</think>", "", token, flags=re.DOTALL
                    )
                    if not token:
                        continue

                    if not first_token_seen:
                        ttft = time.time() - start
                        logger.info(
                            f"[Ollama Streaming] Time to first token: {ttft:.3f}s"
                        )
                        first_token_seen = True

                    total_tokens += 1
                    yield token

                if data.get("done", False):
                    new_context = data.get("context", [])
                    if new_context:
                        self._session_contexts[session_id] = new_context
                        logger.info(
                            f"[KV Cache] Updated context after streaming "
                            f"for session {session_id} (size: {len(new_context)})"
                        )

                    total_duration = time.time() - start
                    logger.info(
                        f"[Ollama Streaming] Complete: {total_tokens} tokens "
                        f"in {total_duration:.2f}s | "
                        f"prompt_tokens={data.get('prompt_eval_count', 0)} "
                        f"completion_tokens={data.get('eval_count', 0)}"
                    )

    # ------------------------------------------------------------------
    # session management
    # ------------------------------------------------------------------
    def reset_session(self, session_id: str) -> None:
        removed = self._session_contexts.pop(session_id, None)
        if removed:
            logger.info(
                f"[KV Cache] Cleared context for session {session_id} "
                f"(was size: {len(removed)})"
            )
        else:
            logger.info(
                f"[KV Cache] No context to clear for session {session_id}"
            )

    def get_context_size(self, session_id: str) -> int:
        """Return the number of tokens in the cached context."""
        ctx = self._session_contexts.get(session_id)
        return len(ctx) if ctx else 0
