from langchain_ollama import ChatOllama
from langchain.llms.base import LLM
from typing import Optional, List
from pydantic import PrivateAttr
import re


class MyServerLLM(LLM):
    """
    Custom LLM wrapper using ChatOllama to call a locally running Ollama model.
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
        """
        try:
            response = self._client.invoke(prompt, stop=stop)
            cleaned_text = re.sub(
                r"<think>.*?</think>", "", response.content, flags=re.DOTALL
            )
            return cleaned_text
        except Exception as e:
            raise RuntimeError(f"Failed to call Ollama locally: {e}") from e
