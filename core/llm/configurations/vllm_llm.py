import os
import re
import threading
from typing import Dict, List, Optional, Tuple

from langchain_core.language_models import LLM
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr

from core.config import settings

# Concurrency limit — mirrors local_llm.py semaphore pattern
VLLM_CONCURRENCY = int(os.environ.get("VLLM_NUM_PARALLEL", 4))

# Global dictionary of semaphores per (model, port)
_locks: Dict[Tuple[str, int], threading.Semaphore] = {}
_locks_global_lock = threading.Lock()


def _model_port_lock(model: str, port: int):
    """Return a semaphore for the given (model, port) key."""
    key = (model, port)
    with _locks_global_lock:
        if key not in _locks:
            _locks[key] = threading.Semaphore(VLLM_CONCURRENCY)
    return _locks[key]


class MyServerLLM(LLM):
    """
    Custom LLM wrapper using ChatOpenAI to call a vLLM server via its
    OpenAI-compatible API.  Drop-in replacement for the Ollama-based
    MyServerLLM in local_llm.py.
    """

    model: str
    port: int
    _client: ChatOpenAI = PrivateAttr()

    def __init__(self, model: str, port: int = 8010, **kwargs):
        print(
            f"Initializing vLLM MyServerLLM with model={settings.VLLM_MODEL or model} "
            f"at {settings.VLLM_BASE_URL}"
        )
        super().__init__(model=model, port=port, **kwargs)

        from core.constants import MODEL_OUTPUT_TOKENS

        self._client = ChatOpenAI(
            model=settings.VLLM_MODEL or model,
            base_url=settings.VLLM_BASE_URL,
            api_key=settings.VLLM_API_KEY,
            timeout=1000,
            max_tokens=MODEL_OUTPUT_TOKENS,
        )

    @property
    def _llm_type(self) -> str:
        return "vllm_local_llm"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        Call the vLLM server using ChatOpenAI (OpenAI-compatible endpoint).
        Limits concurrent requests per (model, port) via semaphore.
        """
        sem = _model_port_lock(self.model, self.port)
        sem.acquire()
        try:
            print(
                f"Processing vLLM request for model={settings.VLLM_MODEL or self.model}"
            )
            response = self._client.invoke(prompt, stop=stop)
            # Strip thinking/reasoning tags (same as local_llm.py)
            cleaned_text = re.sub(
                r"<think>.*?</think>", "", response.content, flags=re.DOTALL
            )
            cleaned_text = re.sub(
                r"<reasoning>.*?</reasoning>", "", cleaned_text, flags=re.DOTALL
            )
            return cleaned_text.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to call vLLM server: {e}") from e
        finally:
            sem.release()
