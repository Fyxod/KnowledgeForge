import time
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=1,
    google_api_key=settings.GOOGLE_API_KEY,
)

# Add ollama later
