import time
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings
from core.constants import QUERY_LLM, REWRITE_QUERY_LLM, SUMMARIZER_LLM
from google import genai
import google.api_core.exceptions
from typing import Any, List, Type
import asyncio

import sys

sys.setrecursionlimit(5000)

API_KEYS = [
    settings.GOOGLE_API_KEY_1,
    settings.GOOGLE_API_KEY_2,
    settings.GOOGLE_API_KEY_3,
    settings.GOOGLE_API_KEY_4,
]

count = 0


async def invoke_llm(model: str, response_schema, contents, remove_thinking=False):
    global count

    for _ in range(len(API_KEYS) * 3):
        api_key = API_KEYS[count % len(API_KEYS)]
        client = genai.Client(api_key=api_key)

        try:
            print("before the llm")

            # config = {
            #     "response_mime_type": "application/json",
            #     "response_schema": response_schema,
            #     "temperature": 0.2,
            #     "max_output_tokens": 200000,
            # }
            
            if remove_thinking:
                config = genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                    max_output_tokens=200000,
                    thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                )
            else:
                config = genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                    max_output_tokens=200000,
                )


            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=str(contents),
                config=config,
            )
            count = (count + 1) % len(API_KEYS)
            if count > 100:
                count = 0
            print("raw response")
            print(response)
            return response.parsed

        except Exception as e:
            print(f"LLM invocation failed with key {count}: {e}")
            count = (count + 1) % len(API_KEYS)
            await asyncio.sleep(2)

    raise RuntimeError("All API keys exhausted or rate-limited.")
