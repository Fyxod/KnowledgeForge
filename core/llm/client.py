import asyncio
import time
from core.config import settings
from google import genai
from openai import AsyncOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from core.constants import SWITCHES, FALLBACK_OPENAI_MODEL, FALLBACK_GEMINI_MODEL

if SWITCHES["REMOTE_GPU"]:
    import core.llm.configurations.remote_llm as llm_module
else:
    import core.llm.configurations.local_llm as llm_module

MyServerLLM = llm_module.MyServerLLM

API_KEYS = [
    settings.API_KEY_1,
    settings.API_KEY_2,
    settings.API_KEY_3,
    settings.API_KEY_4,
    settings.API_KEY_5,
]

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API)
MAX_RETRIES = 8  # Total attempts across all LLMs

count = 0


async def invoke_llm(
    gpu_model,
    response_schema,
    contents,
    port=11434,
    remove_thinking=False,
):
    """
    Unified structured LLM invocation with retries and fallbacks:
    - GPU server
    - Gemini API
    - OpenAI API
    Each returns parsed structured data using the same logic.
    """
    global count

    # Initialize the parser for structured output
    parser = PydanticOutputParser(pydantic_object=response_schema)

    prompt = f"""
    Extract structured data according to this model:
    {parser.get_format_instructions()}

    Input:
    {contents}
    """

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n=== Attempt {attempt}/{MAX_RETRIES} ===")

        # === 1. GPU SERVER ===
        if gpu_model:
            try:
                print("Trying GPU server...")
                gpu_llm = MyServerLLM(model=gpu_model, port=port)
                s = time.time()
                llm_output = await asyncio.to_thread(gpu_llm._call, prompt)
                e = time.time()
                print(f"Success via GPU server, LLM call took {e - s:.2f}s")
                structured = parser.parse(llm_output)
                return structured
            except Exception as e:
                print(f"GPU server failed failed at port {port}: {e}")

            if port == 11435:
                temp_port = 11434
                try:
                    print(f"Retrying GPU server on alternate port {temp_port}...")
                    gpu_llm = MyServerLLM(model=gpu_model, port=temp_port)
                    s = time.time()
                    llm_output = await asyncio.to_thread(gpu_llm._call, prompt)
                    e = time.time()
                    print(f"Success via GPU server, LLM call took {e - s:.2f}s")
                    structured = parser.parse(llm_output)
                    return structured
                except Exception as e:
                    print(f"GPU server failed at alternate port {temp_port}: {e}")

        # === 2. GEMINI FALLBACK ===
        if SWITCHES["FALLBACK_TO_GEMINI"]:
            print("Falling back to Gemini...")

            for _ in range(len(API_KEYS)):
                api_key = API_KEYS[count % len(API_KEYS)]
                count = (count + 1) % len(API_KEYS)
                client = genai.Client(api_key=api_key)
                s = time.time()
                try:
                    config = genai.types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=200000,
                        response_mime_type="text/plain",
                        safety_settings=[],
                    )

                    if remove_thinking:
                        config.thinking_config = genai.types.ThinkingConfig(
                            thinking_budget=0
                        )

                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=FALLBACK_GEMINI_MODEL,
                            contents=prompt,
                            config=config,
                        ),
                        timeout=80,
                    )

                    # Try to extract the raw text content
                    raw_output = None
                    try:
                        raw_output = response.text or str(response)
                    except Exception:
                        raw_output = str(response)

                    structured = parser.parse(raw_output)
                    e = time.time()
                    print(f"Success via Gemini, LLM call took {e - s:.2f}s")
                    return structured

                except asyncio.TimeoutError:
                    print("Gemini timeout — switching key...")
                except Exception as e:
                    print(f"Gemini error: {e}")
                    await asyncio.sleep(0.2)

        # === 3. OPENAI FALLBACK ===
        if SWITCHES["FALLBACK_TO_OPENAI"]:
            try:
                print("Falling back to OpenAI...")
                s = time.time()
                response = await openai_client.chat.completions.create(
                    model=FALLBACK_OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )

                raw_output = response.choices[0].message.content
                structured = parser.parse(raw_output)
                e = time.time()
                print(f"Success via OpenAI, LLM call took {e - s:.2f}s")
                return structured

            except Exception as e:
                print(f"OpenAI fallback error: {e}")

        await asyncio.sleep(2)

    # If all attempts exhausted
    raise RuntimeError(f"All {MAX_RETRIES} fallback attempts failed.")
