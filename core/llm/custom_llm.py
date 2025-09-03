import requests
from langchain.llms.base import LLM
from typing import Optional, List

global_url = "https://llm.katiyr.xyz/query?model=gemma-lat:latest"

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
            return data.get("output", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call GPU LLM server: {e}") from e
