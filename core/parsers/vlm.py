"""
VLM (Visual Language Model) Parser Module

Uses Ollama's vision-capable models (e.g., qwen2.5-vl) to extract
structured text from presentation slides, complex PDF pages, and
other visually-rich documents that standard OCR misses.

Follows the project's async httpx pattern (see core/llm/unload_ollama_model.py).
"""

import httpx
import base64
import time
import traceback

from core.config import settings
from core.constants import PORT1, VLM_MODEL

LOCAL_BASE_URL = settings.LOCAL_BASE_URL

# Prompt tuned for slide/document extraction
VLM_EXTRACTION_PROMPT = (
    "You are an intelligent document parser. "
    "Analyze this image and extract ALL content into structured Markdown.\n"
    "Rules:\n"
    "- Transcribe every text element: titles, headers, bullet points, paragraphs, footnotes.\n"
    "- If there are tables, output them as proper Markdown tables.\n"
    "- If there are charts or diagrams, describe the data points, axes, labels, and trends.\n"
    "- Preserve the logical reading order (top-to-bottom, left-to-right).\n"
    "- Do NOT describe visual styling (colors, fonts, layout) unless it conveys meaning.\n"
    "- Output ONLY the extracted Markdown. No filler text like 'Here is the content'."
)


def _encode_image_base64(image_input) -> str:
    """Encode an image file path or raw bytes to a base64 string."""
    if isinstance(image_input, str):
        with open(image_input, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    elif isinstance(image_input, bytes):
        return base64.b64encode(image_input).decode("utf-8")
    else:
        raise TypeError(f"Expected str (path) or bytes, got {type(image_input)}")


async def vlm_parse_slide(image_input, port: int = PORT1) -> str:
    """
    Send an image to Ollama VLM for structured text extraction.

    Args:
        image_input: File path (str) or raw PNG bytes.
        port: Ollama API port (default: PORT1 from constants).

    Returns:
        Extracted Markdown string, or "" on failure.
    """
    try:
        start_time = time.time()
        image_b64 = _encode_image_base64(image_input)

        url = f"{LOCAL_BASE_URL}:{port}/api/generate"

        payload = {
            "model": VLM_MODEL,
            "prompt": VLM_EXTRACTION_PROMPT,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.1,   # Low temp for factual extraction
                "num_ctx": 4096,      # Sufficient for most slides
            },
        }

        print(f"[VLM] Sending page to Ollama ({VLM_MODEL}) on port {port}...")

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        result = response.json()
        content = result.get("response", "").strip()

        elapsed = time.time() - start_time
        print(f"[VLM] Completed in {elapsed:.2f}s  |  {len(content)} chars extracted.")

        return content

    except httpx.ConnectError:
        print(
            f"[VLM] Connection refused at {LOCAL_BASE_URL}:{port}. "
            "Is Ollama running? Try: ollama serve"
        )
        return ""
    except httpx.TimeoutException:
        print(f"[VLM] Request timed out after 180s for model {VLM_MODEL}.")
        return ""
    except httpx.HTTPStatusError as e:
        print(f"[VLM] HTTP error: {e}")
        return ""
    except Exception as e:
        print(f"[VLM] Unexpected error: {e}")
        traceback.print_exc()
        return ""
