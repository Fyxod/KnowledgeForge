from pydantic_settings import BaseSettings
from dotenv import load_dotenv

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
    USE_VISION_MODEL: bool = False  # Set to True in .env to force VLM for all PDF pages
    LOCAL_BASE_URL : str = "http://localhost"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
