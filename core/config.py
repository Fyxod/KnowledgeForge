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

    # INTERNAL API Configuration (defaults to disabled for backward compatibility)
    INTERNAL_BASE_URL: str = ""
    INTERNAL_CLIENT_KEY: str = ""
    INTERNAL_API_TOKEN: str = ""
    INTERNAL_USER_EMAIL: str = ""
    INTERNAL_MODEL_ID: str = ""
    USE_INTERNAL: bool = False  # Set to True in .env to enable INTERNAL API

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
