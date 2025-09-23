import requests
from langchain.llms.base import LLM
from typing import Optional, List
import re
from core.config import settings

QUERY_URL = settings.NVIDIA_URL

# Use Nemotron Nano 2 as the custom llm
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
                json={"prompt": prompt, "reasoning": True},
                timeout=500,
            )
            response.raise_for_status()
            data = response.json()
            cleaned_text = re.sub(r"(</?think>.*?</think>|</?think>)", "", data.get("response", ""), flags=re.DOTALL)

            cleaned_text = cleaned_text.strip()
            print("cleaned ",cleaned_text)
            return cleaned_text
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call GPU LLM server: {e}") from e
