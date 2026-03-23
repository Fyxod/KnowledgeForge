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
    VLLM_MAIN_URL: str = "http://localhost:9000/v1"        # vLLM main LLM OpenAI-compat endpoint
    VLLM_VLM_URL: str = "http://localhost:9001/v1"          # vLLM VLM OpenAI-compat endpoint
    VLLM_MAIN_MODEL: str = "openai/gpt-oss-20b"             # Use "openai/gpt-oss-120b" for 120B variant
    VLLM_VLM_MODEL: str = "cyankiwi/Qwen3.5-9B-AWQ-4bit"   # Qwen3.5-9B AWQ — vision+text+reasoning (~6GB VRAM)
    VLLM_DRAFT_MODEL: str = ""                              # Speculative decoding draft model, empty = disabled
    VLLM_GLM_OCR_MODEL: str = "zai-org/GLM-OCR"              # GLM-OCR 0.9B vLLM backend (port 9090); SDK server on port 5002
    VLLM_GPU_MEMORY_UTILIZATION: float = 0.57               # gpt-oss-20b MXFP4: 0.57×48=27.4GB → ~16GB weights + ~11.4GB KV → ~90K theoretical max
    VLLM_VLM_GPU_MEMORY_UTILIZATION: float = 0.18           # Qwen3.5-9B AWQ ~6GB; 0.18×48=8.6GB → ~2.6GB KV (sufficient for image tasks)
    VLLM_MAX_MODEL_LEN: int = 65536                         # 64K — safe within ~90K ceiling; total model VRAM ~38.4GB (40GB cap)
    VLLM_VLM_MAX_MODEL_LEN: int = 32768                     # Qwen3.5-9B: 32K for image tasks; raise to 262144 when running VLM alone

    # ── Unified Qwen3.5-9B mode ─────────────────────────────────────────────────
    # VLLM_MODE=gpt-oss (default): gpt-oss-20b on port 9000, Qwen AWQ VLM on port 9001
    # VLLM_MODE=qwen-unified: single Qwen3.5-9B BF16 on port 9000 handles both LLM + VLM
    VLLM_MODE: str = "gpt-oss"
    VLLM_UNIFIED_MODEL: str = "Qwen/Qwen3.5-9B"  # BF16 full model (~18 GB VRAM) used in unified mode

    @property
    def effective_vlm_url(self) -> str:
        """VLM endpoint — port 9000 (shared with main LLM) in unified mode, else port 9001."""
        return self.VLLM_MAIN_URL if self.VLLM_MODE == "qwen-unified" else self.VLLM_VLM_URL

    @property
    def effective_vlm_model(self) -> str:
        """VLM model name — unified BF16 Qwen in unified mode, else AWQ Qwen on port 9001."""
        return self.VLLM_UNIFIED_MODEL if self.VLLM_MODE == "qwen-unified" else self.VLLM_VLM_MODEL

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
