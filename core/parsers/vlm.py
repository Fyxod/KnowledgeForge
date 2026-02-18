"""
VLM (Visual Language Model) Parser Module

Uses Ollama's vision-capable models (e.g., qwen3-vl:8b) to extract
structured text from presentation slides, complex PDF pages, and
other visually-rich documents that standard OCR misses.

Follows the project's async httpx pattern (see core/llm/unload_ollama_model.py).
"""

import asyncio
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
    Send a single image to Ollama VLM for structured text extraction.

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
            "keep_alive": 300,    # Keep model loaded for 5 min between calls
            "options": {
                "temperature": 0.1,   # Low temp for factual extraction
                "num_ctx": 8192,      # More context for complex pages
                "num_predict": 4096,  # Cap output to avoid runaway generation
            },
        }

        print(f"[VLM] Sending page to Ollama ({VLM_MODEL}) on port {port}...")

        async with httpx.AsyncClient(timeout=240) as client:
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
        print(f"[VLM] Request timed out after 240s for model {VLM_MODEL}.")
        return ""
    except httpx.HTTPStatusError as e:
        print(f"[VLM] HTTP error: {e}")
        return ""
    except Exception as e:
        print(f"[VLM] Unexpected error: {e}")
        traceback.print_exc()
        return ""


async def vlm_parse_concurrent(
    images: list[bytes],
    page_labels: list[str] | None = None,
    port: int = PORT1,
    max_concurrent: int = 3,
) -> list[str]:
    """
    Process multiple pages concurrently using async single-page VLM calls.

    This is faster than sequential processing (N calls in ~N/max_concurrent time)
    while being more reliable than multi-image batching (which can timeout and
    cause VRAM spikes).

    Args:
        images: List of raw PNG bytes, one per page.
        page_labels: Optional labels for logging (e.g. ["Page 1", "Slide 3"]).
        port: Ollama API port (default: PORT1 from constants).
        max_concurrent: Max simultaneous VLM calls (default: 3, balance speed vs VRAM).

    Returns:
        List of extracted Markdown strings, one per input image.
        Empty string for pages where extraction failed.
    """
    if not images:
        return []

    total = len(images)
    labels = page_labels or [f"Page {i+1}" for i in range(total)]
    semaphore = asyncio.Semaphore(max_concurrent)

    print(f"[VLM] Concurrent processing: {total} pages, max {max_concurrent} at a time")
    overall_start = time.time()

    async def _process_one(idx: int, img_bytes: bytes) -> str:
        async with semaphore:
            print(f"[VLM] Starting {labels[idx]}...")
            result = await vlm_parse_slide(img_bytes, port=port)
            if result:
                print(f"[VLM] {labels[idx]} done ({len(result)} chars)")
            else:
                print(f"[VLM] {labels[idx]} returned empty")
            return result

    # Launch all tasks, semaphore limits concurrency
    tasks = [_process_one(i, img) for i, img in enumerate(images)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to empty strings
    final = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"[VLM] {labels[i]} failed with error: {r}")
            final.append("")
        else:
            final.append(r or "")

    elapsed = time.time() - overall_start
    extracted = sum(1 for r in final if r)
    print(f"[VLM] Concurrent processing complete: {extracted}/{total} pages in {elapsed:.2f}s")
    return final
