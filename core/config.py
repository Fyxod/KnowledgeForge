from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DATABASE_NAME: str = "bedrock"
    GOOGLE_API_KEY_1: str
    GOOGLE_API_KEY_2: str
    GOOGLE_API_KEY_3: str
    GOOGLE_API_KEY_4: str
    GOOGLE_API_KEY_5: str
    GOOGLE_API_KEY_6: str
    GOOGLE_API_KEY_7: str
    GOOGLE_API_KEY_8: str
    GOOGLE_API_KEY_9: str
    GOOGLE_API_KEY_10: str
    GOOGLE_API_KEY_11: str
    GOOGLE_API_KEY_12: str
    GOOGLE_API_KEY_13: str
    GOOGLE_API_KEY_14: str
    GOOGLE_API_KEY_15: str
    GOOGLE_API_KEY_16: str
    GOOGLE_API_KEY_17: str
    LLM_URL: str

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
