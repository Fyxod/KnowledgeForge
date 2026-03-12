import asyncio
import itertools
import time

from google import genai
from langchain_core.output_parsers import PydanticOutputParser
from openai import AsyncOpenAI

from core.config import settings
from core.constants import FALLBACK_GEMINI_MODEL, FALLBACK_OPENAI_MODEL, SWITCHES
from core.utils.llm_output_sanitizer import parse_llm_json, sanitize_llm_json

if SWITCHES["REMOTE_GPU"]:
    import core.llm.configurations.remote_llm as llm_module
else:
    import core.llm.configurations.local_llm as llm_module

MyServerLLM = llm_module.MyServerLLM

# Cache LLM client instances to avoid repeated initialization overhead
_llm_cache = {}


def _get_cached_llm(model: str, port: int) -> MyServerLLM:
    """Return a cached MyServerLLM instance, creating one if needed."""
    key = (model, port)
    if key not in _llm_cache:
        _llm_cache[key] = MyServerLLM(model=model, port=port)
    return _llm_cache[key]


API_KEYS = [
    settings.API_KEY_1,
    settings.API_KEY_2,
    settings.API_KEY_3,
    settings.API_KEY_4,
    settings.API_KEY_5,
    settings.API_KEY_6,
]

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API)
MAX_RETRIES = 4  # Reduced from 8: JSON sanitizer + json_repair handles most parse errors on first attempt

# Thread-safe API key cycling
_api_key_cycle = itertools.cycle(API_KEYS)
_api_key_lock = asyncio.Lock()


async def _next_api_key():
    """Get the next API key in round-robin fashion, safely under concurrency."""
    async with _api_key_lock:
        return next(_api_key_cycle)


def _try_parse(raw_output: str, parser, response_schema):
    """
    Attempt to parse LLM output with sanitization and repair fallbacks.

    Strategy:
    1. Sanitize + PydanticOutputParser.parse() (existing path, now with pre-processing)
    2. parse_llm_json() with json_repair + model_validate (handles malformed JSON)

    Returns parsed structured data or raises on failure.
    """
    cleaned = sanitize_llm_json(raw_output)

    # Strategy 1: Sanitized output through existing parser
    try:
        return parser.parse(cleaned)
    except Exception:
        pass

    # Strategy 2: json_repair + Pydantic model_validate (no LLM call needed)
    return parse_llm_json(raw_output, response_schema)


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

    # Initialize the parser for structured output
    parser = PydanticOutputParser(pydantic_object=response_schema)

    prompt = f"""
    Extract structured data according to this model:
    {parser.get_format_instructions()}

    Input:
    {contents}

    CRITICAL OUTPUT RULES:
    1. Output must be valid JSON.
    2. Escape newlines as \\n and tabs as \\t within JSON strings.
    3. If you generate internal reasoning (e.g. inside <think> tags), you MUST produce the final JSON object AFTER the closing </think> tag.
    4. Do not output any text before or after the JSON object.
    """

    # Track the last failed output and parse error for self-correction context
    last_failed_output = None
    last_parse_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n=== Attempt {attempt}/{MAX_RETRIES} ===")

        # Build the effective prompt — append correction context if a previous
        # attempt produced output that failed parsing
        effective_prompt = prompt
        if last_failed_output and last_parse_error:
            effective_prompt = (
                f"{prompt}\n\n"
                "--- PREVIOUS ATTEMPT FAILED ---\n"
                "Your previous output could not be parsed. Fix the errors and output valid JSON only.\n\n"
                f"Previous output (rejected):\n{last_failed_output[:2000]}\n\n"
                f"Parse error:\n{last_parse_error}\n\n"
                "Fix the above errors and return ONLY valid JSON matching the schema."
            )
            print(f"[Self-correction] Injecting previous output + error into prompt")

        # === 1. GPU SERVER ===
        if gpu_model:
            llm_output = None
            try:
                print("Trying GPU server...")
                gpu_llm = _get_cached_llm(gpu_model, port)
                s = time.time()
                llm_output = await asyncio.to_thread(gpu_llm._call, effective_prompt)
                e = time.time()
                print(f"Success via GPU server, LLM call took {e - s:.2f}s")
                structured = _try_parse(llm_output, parser, response_schema)
                return structured
            except Exception as e:
                error_str = str(e)
                print(f"GPU server failed at port {port}: {error_str}")
                # LLM produced output but parsing failed — retry with correction context
                if llm_output:
                    last_failed_output = llm_output
                    last_parse_error = error_str
                    print(f"[Self-correction] Captured failed output ({len(llm_output)} chars) for next attempt")
                    continue  # Skip fallbacks, retry on same port with correction

        # === 2. GEMINI FALLBACK ===
        if SWITCHES["FALLBACK_TO_GEMINI"]:
            print("Falling back to Gemini...")

            for _ in range(len(API_KEYS)):
                api_key = await _next_api_key()
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
                            contents=effective_prompt,
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

                    structured = _try_parse(raw_output, parser, response_schema)
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
                    messages=[{"role": "user", "content": effective_prompt}],
                    temperature=0.2,
                )

                raw_output = response.choices[0].message.content
                structured = _try_parse(raw_output, parser, response_schema)
                e = time.time()
                print(f"Success via OpenAI, LLM call took {e - s:.2f}s")
                return structured

            except Exception as e:
                print(f"OpenAI fallback error: {e}")

        await asyncio.sleep(2)

    # If all attempts exhausted
    raise RuntimeError(f"All {MAX_RETRIES} fallback attempts failed.")
