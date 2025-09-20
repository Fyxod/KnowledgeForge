from core.config import settings
from google import genai
from openai import AsyncOpenAI
from langchain.output_parsers import PydanticOutputParser
import asyncio
import time
from core.constants import SWITCHES, FALLBACK_OPENAI_MODEL
from core.llm.custom_llm import MyServerLLM

API_KEYS = [
    settings.API_KEY_1,
    settings.API_KEY_2,
    settings.API_KEY_3,
    settings.API_KEY_4,
    settings.API_KEY_5,
]

openai_client = AsyncOpenAI(api_key=settings.VISION_API)
MAX_RETRIES = 8  # Total attempts across all LLMs

count = 0


async def invoke_llm(
    gpu_model,
    response_schema,
    contents,
    fallback_model,
    port=11434,
    remove_thinking=False,
):
    """
    Structured LLM invocation with retries and fallbacks:
    1. Custom GPU server (via MyServerLLM)
    2. Google API keys
    3. OpenAI
    Retries up to `max_retries` times across the whole chain.
    """

    global count

    # Initialize the parser for structured output
    parser = PydanticOutputParser(pydantic_object=response_schema)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n=== Attempt {attempt}/{MAX_RETRIES} ===")
        # 1. Try GPU server first
        if gpu_model:
            try:
                print("Trying GPU server first...")
                print("client received gpu_model:", gpu_model, "port:", port)
                gpu_llm = MyServerLLM(model=gpu_model, port=port)
                prompt = f"""
                Extract structured data according to this model:
                {parser.get_format_instructions()}

                Input:
                {contents}
                """
                s = time.time()
                llm_output = await asyncio.to_thread(gpu_llm._call, prompt)
                e = time.time()
                print(f"GPU LLM call took {e - s:.2f} seconds")
                print(llm_output)
                structured = parser.parse(llm_output)
                print("Success via GPU server")
                return structured
            except Exception as e:
                print(f"GPU server failed: {e}, ")

        if SWITCHES["FALLBACK_TO_GEMINI"]:
            print("Falling back to Gemini API...")
            # 2. Loop through fallback API keys
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
                            thinking_config=genai.types.ThinkingConfig(
                                thinking_budget=0
                            ),
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
                            model=fallback_model,
                            contents=str(contents),
                            config=config,
                        ),
                        timeout=80,
                    )

                    return response.parsed

                except asyncio.TimeoutError:
                    print("Gemini API timeout, switching key...")
                except Exception as e:
                    print(f"Gemini API error: {e}")
                    await asyncio.sleep(0.1)

        # 3. Fallback to OpenAI
        if SWITCHES["FALLBACK_TO_OPENAI"]:
            try:
                print("Falling back to OpenAI...")
                response = await openai_client.chat.completions.create(
                    model=FALLBACK_OPENAI_MODEL,
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
        await asyncio.sleep(2)

    # If all attempts exhausted
    raise RuntimeError(f"All {MAX_RETRIES} LLM fallback attempts failed")
