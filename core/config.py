from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DATABASE_NAME: str = "bedrock"
    MODE: str = "development"
    API_KEY_1: str
    API_KEY_2: str
    API_KEY_3: str
    API_KEY_4: str
    API_KEY_5: str
    API_KEY_6: str
    OPENAI_API: str
    QUERY_URL: str
    VISION_URL: str
    MAIN_MODEL: str
    REMOTE_GPU: bool = False
    USE_VISION_MODEL: bool = True  # VLM runs on every page/slide (PDF, DOCX, PPTX). Set False in .env to disable.
    LOCAL_BASE_URL: str = "http://localhost"

    # ── vLLM endpoints ──────────────────────────────────────────────────────────
    VLLM_MAIN_URL: str = "http://localhost:8000/v1"        # vLLM main LLM OpenAI-compat endpoint
    VLLM_VLM_URL: str = "http://localhost:8001/v1"          # vLLM VLM OpenAI-compat endpoint
    VLLM_MAIN_MODEL: str = ""                               # HuggingFace model ID or local path
    VLLM_VLM_MODEL: str = "Qwen/Qwen2-VL-7B-Instruct-AWQ"  # Multimodal model for slide/PDF parsing
    VLLM_DRAFT_MODEL: str = ""                              # Speculative decoding draft model, empty = disabled
    VLLM_GPU_MEMORY_UTILIZATION: float = 0.55               # For main LLM instance (leaves room for VLM + embeddings)
    VLLM_VLM_GPU_MEMORY_UTILIZATION: float = 0.20           # For VLM instance
    VLLM_MAX_MODEL_LEN: int = 131072                        # Context window for main LLM

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
