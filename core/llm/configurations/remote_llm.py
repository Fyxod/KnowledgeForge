import requests
from langchain_core.language_models import LLM
from typing import Optional, List
import re
from core.config import settings

QUERY_URL = settings.QUERY_URL


class MyServerLLM(LLM):
    """
    Custom LLM wrapper for a GPU-hosted LLM accessible via HTTP.
    Supports LangChain-style calls.
    """

    model: str
    url: str

    def __init__(self, model: str, port: int = 11434, **kwargs):
        print(f"Initializing MyServerLLM with model={model} at port={port}")
        super().__init__(
            model=model, url=f"{QUERY_URL}?model={model}&port={port}", **kwargs
        )

    @property
    def _llm_type(self) -> str:
        return "custom_server_llm"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        Synchronously call the GPU LLM endpoint.
        """
        try:
            response = requests.post(
                self.url,
                json={"prompt": prompt},
                timeout=600,
            )
            response.raise_for_status()
            data = response.json()
            print(data)
            cleaned_text = re.sub(
                r"<think>.*?</think>",
                "",
                data.get("response", ""),
                flags=re.DOTALL,
                # r"<think>.*?</think>", "", data.get("content", ""), flags=re.DOTALL
            )
            return cleaned_text
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call GPU LLM server: {e}") from e
