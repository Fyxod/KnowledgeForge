from langchain_ollama import ChatOllama
from langchain_core.language_models import LLM
from typing import Optional, List, Tuple, Dict
from pydantic import PrivateAttr
import re
import threading
from contextlib import contextmanager

# Global dictionary of locks per (model, port)
_locks: Dict[Tuple[str, int], threading.Lock] = {}
_locks_global_lock = threading.Lock()  # Protects access to the _locks dict


@contextmanager
def model_port_lock(model: str, port: int):
    """
    Context manager that ensures only one request per (model, port)
    is processed at a time. Blocks others until the lock is released.
    """
    key = (model, port)

    # Ensure thread-safe creation of locks
    with _locks_global_lock:
        if key not in _locks:
            _locks[key] = threading.Lock()

    lock = _locks[key]
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


class MyServerLLM(LLM):
    """
    Custom LLM wrapper using ChatOllama to call a locally running Ollama model.
    Ensures only one request per (model, port) is processed at a time.
    """

    model: str
    port: int
    _client: ChatOllama = PrivateAttr()

    def __init__(self, model: str, port: int = 11434, **kwargs):
        print(f"Initializing MyOllamaLLM with model={model} at port={port}")
        super().__init__(model=model, port=port, **kwargs)

        self._client = ChatOllama(
            model=model, base_url=f"http://localhost:{port}", timeout=1000, **kwargs
        )

    @property
    def _llm_type(self) -> str:
        return "ollama_local_llm"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        Call the local Ollama model using ChatOllama.
        Blocks concurrent requests for the same (model, port).
        """
        with model_port_lock(self.model, self.port):
            print(f"Processing request for model={self.model}, port={self.port}")
            try:
                response = self._client.invoke(prompt, stop=stop)
                cleaned_text = re.sub(
                    r"<think>.*?</think>", "", response.content, flags=re.DOTALL
                )
                return cleaned_text
            except Exception as e:
                raise RuntimeError(f"Failed to call Ollama locally: {e}") from e
