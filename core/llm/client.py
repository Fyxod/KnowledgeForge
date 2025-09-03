from core.config import settings
from google import genai
from openai import AsyncOpenAI
from langchain.output_parsers import PydanticOutputParser
import asyncio
import sys

from core.llm.custom_llm import MyServerLLM

sys.setrecursionlimit(5000)

API_KEYS = [
    settings.API_KEY_1,
    settings.API_KEY_2,
    settings.API_KEY_3,
    settings.API_KEY_4,
    settings.API_KEY_5,
]

openai_client = AsyncOpenAI(api_key=settings.VISION_API)
OPENAI_MODEL = "gpt-4o-mini"

count = 0

async def invoke_llm(model: str, response_schema, contents, remove_thinking=False, gpu_url="https://llm.katiyar.xyz?model=gemma-lat"):
    """
    Structured LLM invocation with fallbacks:
    1. Custom GPU server (via MyServerLLM)
    2. Google API keys
    3. OpenAI
    """

    global count

    # Initialize the parser for structured output
    parser = PydanticOutputParser(pydantic_object=response_schema)

    # 1. Try GPU server first
    if gpu_url:
        try:
            print("Trying GPU server first...")
            gpu_llm = MyServerLLM()
            prompt = f"""
            Extract structured data according to this model:
            {parser.get_format_instructions()}

            Input:
            {contents}
            """
            llm_output = await asyncio.to_thread(gpu_llm._call, prompt)
            print(llm_output)
            structured = parser.parse(llm_output)
            print(structured)
            return structured
        except Exception as e:
            print(f"GPU server failed: {e}, switching to API keys...")

    # 2. Loop through API keys
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
                    max_output_tokens=200000,
                    safety_settings=[],
                )

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=str(contents),
                    config=config,
                ),
                timeout=45,
            )

            print("Google API success")
            print(response)
            return response.parsed

        except asyncio.TimeoutError:
            print("Google API timeout, switching key...")
        except Exception as e:
            print(f"Google API error: {e}")
            await asyncio.sleep(0.1)

    # 3. Fallback to OpenAI
    try:
        print("Falling back to OpenAI...")
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": str(contents)}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": response_schema.model_json_schema(),
                },
            },
            temperature=0.2,
        )

        raw_json = response.choices[0].message.content
        structured = response_schema.model_validate_json(raw_json)
        print(structured)
        return structured

    except Exception as e:
        print(f"OpenAI fallback error: {e}")
        await asyncio.sleep(0.2)

    raise RuntimeError("All LLM fallbacks failed")

