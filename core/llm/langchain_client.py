import time
import asyncio
from typing import Any, List, Type

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from core.config import settings

import sys
sys.setrecursionlimit(5000)

API_KEYS = [
    settings.GOOGLE_API_KEY_1,
    settings.GOOGLE_API_KEY_2,
    settings.GOOGLE_API_KEY_3,
    settings.GOOGLE_API_KEY_4,
]

count = 0


async def invoke_llm(
    model: str,
    response_schema: Type[Any],
    contents: List[dict],
):
    """
    Calls Google's LLM using LangChain's ChatGoogleGenerativeAI
    with structured output parsing.

    Args:
        model: LLM model name (e.g., "gemini-1.5-pro")
        response_schema: Pydantic model for structured response
        contents: List of input dicts/messages

    Returns:
        Parsed structured output (Pydantic object)
    """
    global count

    for _ in range(len(API_KEYS) * 3):
        api_key = API_KEYS[count % len(API_KEYS)]

        try:
            llm = ChatGoogleGenerativeAI(
                model=model,
                api_key=api_key,
                temperature=0.2,
                max_output_tokens=100000,
            )

            # structured output parser from schema
            structured_llm = llm.with_structured_output(response_schema)

            response = await structured_llm.ainvoke(str(contents))
            print("normal model", response)
            response = response_schema.model_validate(response)
            print("structured model", response)
            
            count = (count + 1) % len(API_KEYS)
            return response

        except Exception as e:
            print(f"LLM invocation failed with key {count}: {e}")
            count = (count + 1) % len(API_KEYS)
            await asyncio.sleep(2)

    raise RuntimeError("All API keys exhausted or rate-limited.")
