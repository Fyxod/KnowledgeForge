import time
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings
from core.constants import QUERY_LLM, REWRITE_QUERY_LLM, SUMMARIZER_LLM

llm = ChatGoogleGenerativeAI(
    model=QUERY_LLM,
    temperature=1,
    google_api_key=settings.GOOGLE_API_KEY,
)
llm2 = ChatGoogleGenerativeAI(
    model=SUMMARIZER_LLM,
    temperature=1,
    google_api_key=settings.GOOGLE_API_KEY,
)

llm3 = ChatGoogleGenerativeAI(
    model=REWRITE_QUERY_LLM,
    temperature=1,
    google_api_key=settings.GOOGLE_API_KEY,
)

def get_llm(model: str):
    """Get the LLM instance."""
    if model == QUERY_LLM:
        return llm
    elif model == SUMMARIZER_LLM:
        return llm2
    elif model == REWRITE_QUERY_LLM:
        return llm3
    else:
        raise ValueError(f"Unsupported model: {model}") 
# Add ollama later
