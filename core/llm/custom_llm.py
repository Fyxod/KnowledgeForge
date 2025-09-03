import requests
from langchain.llms.base import LLM
from typing import Optional, List
import re

model = "qwen3:8b-30k-8k"
global_url = f"https://llm.katiyar.xyz/query?model={model}"

class MyServerLLM(LLM):
    """
    Custom LLM wrapper for a GPU-hosted LLM accessible via HTTP.
    Supports LangChain-style calls.
    """

    url: str = global_url
    
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
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            print(data)
            # return data.get("output", "")
            cleaned_text = re.sub(r"<think>.*?</think>", "", data["content"], flags=re.DOTALL)
            return cleaned_text
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call GPU LLM server: {e}") from e
