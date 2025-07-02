import asyncio
import os
import re
import aiohttp
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import Settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=1,
    google_api_key=Settings().GOOGLE_API_KEY,
)

# Add ollama later