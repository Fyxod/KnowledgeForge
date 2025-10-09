from pydantic import BaseModel


class OllamaLLMConfig(BaseModel):
    model: str
    port: int
