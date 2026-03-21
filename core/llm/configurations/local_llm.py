# vLLM path — replaces the old Ollama/ChatOllama + semaphore implementation.
# The class interface (MyServerLLM, __init__(model, port), _call, _llm_type) is
# preserved so that core/llm/client.py and _get_cached_llm() work without changes.
# vLLM handles concurrency natively, so no semaphore is needed here.

import re
from typing import List, Optional

from langchain_core.language_models import LLM
from openai import OpenAI

from core.config import settings


class MyServerLLM(LLM):
    """
    Custom LLM wrapper that calls a locally running vLLM instance via its
    OpenAI-compatible API (POST /v1/chat/completions).

    The `port` field is kept for API compatibility with _get_cached_llm(model, port)
    in client.py but is no longer used — the endpoint URL comes from
    settings.VLLM_MAIN_URL instead.

    Concurrency is handled natively by vLLM; the old Ollama semaphore is gone.
    """

    model: str
    port: int  # Kept for API compatibility — ignored; vLLM URL comes from settings

    def __init__(self, model: str, port: int = 11434, **kwargs):
        print(f"Initializing MyServerLLM (vLLM) with model={model} at {settings.VLLM_MAIN_URL}")
        super().__init__(model=model, port=port, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "vllm_local_llm"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        Call the local vLLM instance via OpenAI-compatible chat completions.

        Reads SWITCHES["DISABLE_THINKING"] at call time so UI toggles take effect
        immediately without restarting the server.

        Always strips <think>…</think> and <reasoning>…</reasoning> tags from the
        output as a safety net, even when thinking is nominally disabled.
        """
        from core.constants import SWITCHES

        disable_thinking = SWITCHES.get("DISABLE_THINKING", True)

        extra_body = {}
        if disable_thinking:
            extra_body = {"chat_template_kwargs": {"enable_thinking": False}}

        print(f"[vLLM] Sending request — model={self.model}, disable_thinking={disable_thinking}")

        try:
            client = OpenAI(base_url=settings.VLLM_MAIN_URL, api_key="EMPTY")
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8000,
                extra_body=extra_body if extra_body else None,
            )
            raw_text = response.choices[0].message.content or ""

            # Strip thinking tags regardless — safety net for models that ignore the flag
            cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
            cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
            return cleaned.strip()

        except Exception as e:
            raise RuntimeError(f"Failed to call vLLM locally: {e}") from e
