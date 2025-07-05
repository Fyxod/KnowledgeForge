from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pymongo import MongoClient
import os

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DATABASE_NAME: str = "bedrock"
    GOOGLE_API_KEY: str

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# # MongoDB client and DB instance
# client = MongoClient(settings.DATABASE_URL)
# db = client[settings.DATABASE_NAME]
