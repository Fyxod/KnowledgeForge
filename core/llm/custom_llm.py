import requests
from langchain.llms.base import LLM
from typing import Optional, List
import re

BASE_URL = "https://llm.katiyar.xyz/query"


class MyServerLLM(LLM):
    """
    Custom LLM wrapper for a GPU-hosted LLM accessible via HTTP.
    Supports LangChain-style calls.
    """

    model: str
    url: str

    def __init__(self, model: str, **kwargs):
        super().__init__(model=model, url=f"{BASE_URL}?model={model}", **kwargs)

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
                timeout=200,
            )
            response.raise_for_status()
            data = response.json()
            print(data)
            cleaned_text = re.sub(
                r"<think>.*?</think>", "", data.get("content", ""), flags=re.DOTALL
            )
            return cleaned_text
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call GPU LLM server: {e}") from e
