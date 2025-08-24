from core.config import settings
from google import genai
import asyncio

import sys

sys.setrecursionlimit(5000)

API_KEYS = [
    settings.GOOGLE_API_KEY_14,
    settings.GOOGLE_API_KEY_15,
    settings.GOOGLE_API_KEY_16,
    settings.GOOGLE_API_KEY_17,
    settings.GOOGLE_API_KEY_18,
    settings.GOOGLE_API_KEY_19,
    settings.GOOGLE_API_KEY_20,
    settings.GOOGLE_API_KEY_21,
    settings.GOOGLE_API_KEY_22,
    settings.GOOGLE_API_KEY_23,
    settings.GOOGLE_API_KEY_24,
    settings.GOOGLE_API_KEY_25,
    settings.GOOGLE_API_KEY_26,
    settings.GOOGLE_API_KEY_27,
    settings.GOOGLE_API_KEY_28,
    settings.GOOGLE_API_KEY_1,
    settings.GOOGLE_API_KEY_2,
    settings.GOOGLE_API_KEY_3,
    settings.GOOGLE_API_KEY_4,
    settings.GOOGLE_API_KEY_5,
    settings.GOOGLE_API_KEY_6,
    settings.GOOGLE_API_KEY_7,
    settings.GOOGLE_API_KEY_8,
    settings.GOOGLE_API_KEY_9,
    settings.GOOGLE_API_KEY_10,
    settings.GOOGLE_API_KEY_11,
    settings.GOOGLE_API_KEY_12,
    settings.GOOGLE_API_KEY_13
]

count = 0


async def invoke_llm(model: str, response_schema, contents, remove_thinking=False):
    global count

    for _ in range(len(API_KEYS) * 4):
        api_key = API_KEYS[count % len(API_KEYS)]
        client = genai.Client(api_key=api_key)
        count = (count + 1) % len(API_KEYS)
        
        try:

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
                    safety_settings=[],
                    thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                )
            else:
                config = genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                    safety_settings=[],
                    max_output_tokens=200000,
                )


            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=str(contents),
                config=config,
            )

            print("raw response")
            return response.parsed

        except Exception as e:
            print("ex")
            count = (count + 1) % len(API_KEYS)
            await asyncio.sleep(1)

    raise RuntimeError("All gone")
