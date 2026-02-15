"""
Remote GPU server inference provider.

Communicates with a custom GPU server via HTTP.  Streaming is attempted
via chunked transfer-encoded responses; if the server does not support
it, the provider falls back to a single non-streaming call automatically.
"""

import json
import logging
import re
import time
from typing import AsyncGenerator

import httpx

from core.llm.providers.base import GenerateResult, InferenceProvider

logger = logging.getLogger(__name__)


class RemoteGPUProvider(InferenceProvider):
    """Inference provider for a custom remote GPU LLM server."""

    def __init__(self, query_url: str, model: str, port: int = 11434):
        self.url = f"{query_url}?model={model}&port={port}"
        self.model = model
        self.port = port
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)
        )
        logger.info(
            f"RemoteGPUProvider initialised: model={model}, url={self.url}"
        )

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # ------------------------------------------------------------------
    # generate – full response
    # ------------------------------------------------------------------
    async def generate(self, prompt: str, session_id: str) -> GenerateResult:
        start = time.time()

        response = await self._client.post(
            self.url,
            json={"prompt": prompt},
        )
        response.raise_for_status()
        data = response.json()

        total_duration = time.time() - start
        raw = data.get("response", "") or data.get("content", "")
        cleaned = self._clean(raw)

        logger.info(f"[RemoteGPU] Generated in {total_duration:.2f}s")

        return GenerateResult(
            text=cleaned,
            total_duration=total_duration,
        )

    # ------------------------------------------------------------------
    # stream – attempt chunked, fallback to non-streaming
    # ------------------------------------------------------------------
    async def stream(
        self, prompt: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        start = time.time()
        first_token_seen = False

        try:
            async with self._client.stream(
                "POST",
                self.url,
                json={"prompt": prompt, "stream": True},
            ) as response:
                response.raise_for_status()

                buffer = ""
                async for chunk in response.aiter_text():
                    if not chunk:
                        continue
                    buffer += chunk

                    # Try to parse as newline-delimited JSON
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("response", "") or data.get(
                                "content", ""
                            )
                            token = self._clean(token)
                            if token:
                                if not first_token_seen:
                                    ttft = time.time() - start
                                    logger.info(
                                        f"[RemoteGPU Stream] TTFT: {ttft:.3f}s"
                                    )
                                    first_token_seen = True
                                yield token
                        except json.JSONDecodeError:
                            # Raw text chunk rather than JSON
                            cleaned = self._clean(line)
                            if cleaned:
                                if not first_token_seen:
                                    ttft = time.time() - start
                                    logger.info(
                                        f"[RemoteGPU Stream] TTFT: {ttft:.3f}s"
                                    )
                                    first_token_seen = True
                                yield cleaned

                    # Flush anything remaining in the buffer
                if buffer.strip():
                    try:
                        data = json.loads(buffer)
                        token = data.get("response", "") or data.get(
                            "content", ""
                        )
                        token = self._clean(token)
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        cleaned = self._clean(buffer)
                        if cleaned:
                            yield cleaned

        except (httpx.HTTPStatusError, httpx.StreamError) as exc:
            logger.warning(
                f"[RemoteGPU] Streaming not supported ({exc}), "
                "falling back to non-streaming"
            )
            result = await self.generate(prompt, session_id)
            yield result.text
        except Exception as exc:
            logger.error(
                f"[RemoteGPU Stream] Error: {exc}, falling back to non-streaming"
            )
            try:
                result = await self.generate(prompt, session_id)
                yield result.text
            except Exception as exc2:
                logger.error(f"[RemoteGPU] Fallback also failed: {exc2}")
                raise

        total_duration = time.time() - start
        logger.info(f"[RemoteGPU Stream] Complete in {total_duration:.2f}s")

    # ------------------------------------------------------------------
    # session – no-op (server is stateless)
    # ------------------------------------------------------------------
    def reset_session(self, session_id: str) -> None:
        logger.info(
            f"[RemoteGPU] Session reset for {session_id} (no-op)"
        )
