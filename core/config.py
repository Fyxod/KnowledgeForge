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
    LLM_URL: str

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
