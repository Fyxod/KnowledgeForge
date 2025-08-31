from core.config import settings
from google import genai
from openai import AsyncOpenAI
import asyncio
import sys

sys.setrecursionlimit(5000)

API_KEYS = [
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
    settings.GOOGLE_API_KEY_13,
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
    settings.GOOGLE_API_KEY_29,
    settings.GOOGLE_API_KEY_30,
    settings.GOOGLE_API_KEY_31,
    settings.GOOGLE_API_KEY_32,
    settings.GOOGLE_API_KEY_33,
    settings.GOOGLE_API_KEY_34,
    settings.GOOGLE_API_KEY_35,
    settings.GOOGLE_API_KEY_36,
    settings.GOOGLE_API_KEY_37,
    settings.GOOGLE_API_KEY_38,
    settings.GOOGLE_API_KEY_39,
    settings.GOOGLE_API_KEY_40,
    settings.GOOGLE_API_KEY_41,
    settings.GOOGLE_API_KEY_42,
    settings.GOOGLE_API_KEY_43,
    settings.GOOGLE_API_KEY_44,
    settings.GOOGLE_API_KEY_45,
    settings.GOOGLE_API_KEY_46,
    settings.GOOGLE_API_KEY_47,
    settings.GOOGLE_API_KEY_48,
    settings.GOOGLE_API_KEY_49,
    settings.GOOGLE_API_KEY_50,
    settings.GOOGLE_API_KEY_51,
    settings.GOOGLE_API_KEY_52,
]
openai_client = AsyncOpenAI(api_key=settings.VISION_API)

OPENAI_MODEL = "gpt-4o-mini"
count = 0

async def invoke_llm(model: str, response_schema, contents, remove_thinking=False):
    global count
    
    for pass_num in range(4):
        # Try Gemini via Google GenAI keys
        for _ in range(len(API_KEYS)):
            api_key = API_KEYS[count % len(API_KEYS)]
            client = genai.Client(api_key=api_key)
            count = (count + 1) % len(API_KEYS)

            try:
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
                await asyncio.sleep(0.1)

        
        try:
            print("falling main")
            response = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": str(contents)}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.__name__,
                        "schema": response_schema.model_json_schema()
                    }
                },
                temperature=0.2,
            )
            
            raw_json = response.choices[0].message.content

            structured = response_schema.model_validate_json(raw_json)

            return structured

        except Exception as e:
            print("falling error")
            await asyncio.sleep(0.2)

    raise RuntimeError("All done with fall")
