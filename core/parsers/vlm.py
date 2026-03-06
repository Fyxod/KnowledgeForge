"""
VLM (Visual Language Model) Parser Module

Uses Ollama's vision-capable models (e.g., qwen3-vl:8b) to extract
structured text from presentation slides, complex PDF pages, and
other visually-rich documents that standard OCR misses.

Follows the project's async httpx pattern (see core/llm/unload_ollama_model.py).
"""

import asyncio
import base64
import io
import time
import traceback

import httpx
from PIL import Image

from core.config import settings
from core.constants import PORT1, VLM_MODEL

LOCAL_BASE_URL = settings.LOCAL_BASE_URL

# Max image dimension (pixels) for VLM input — smaller images process faster and more reliably on 8B VLMs
VLM_MAX_IMAGE_DIM = 1280
VLM_RETRY_IMAGE_DIM = 800  # Even smaller for retry attempts

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

# Simpler prompt for retry — less instruction overhead helps smaller VLMs focus
VLM_RETRY_PROMPT = (
    "Extract all text content from this image. "
    "Include titles, bullet points, table data, and any text visible in charts or diagrams. "
    "Output as Markdown. No filler text."
)

# Specialized prompt for extracting flowcharts and ERDs into code
VLM_MERMAID_PROMPT = (
    "You are an expert graph transcription AI. Analyze this image. "
    "If it contains a flowchart, architectural diagram, or Entity-Relationship Diagram (ERD), "
    "extract the exact nodes, edges, decisions, and relationships. "
    "Output the result STRICTLY as valid `Mermaid.js` syntax representing the graph. "
    "Do not describe the graph in English; write ONLY the Mermaid code block that generates it."
)


def _resize_image(image_bytes: bytes, max_dim: int) -> bytes:
    """Resize image so its longest side is at most max_dim pixels. Returns PNG bytes."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    if max(w, h) <= max_dim:
        return image_bytes  # Already small enough

    scale = max_dim / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    print(f"[VLM] Resized image {w}x{h} → {new_w}x{new_h} (max_dim={max_dim})")
    return buf.getvalue()


def _encode_image_base64(image_input, max_dim: int = VLM_MAX_IMAGE_DIM) -> str:
    """Encode an image file path or raw bytes to a base64 string, resizing if needed."""
    if isinstance(image_input, str):
        with open(image_input, "rb") as f:
            raw = f.read()
    elif isinstance(image_input, bytes):
        raw = image_input
    else:
        raise TypeError(f"Expected str (path) or bytes, got {type(image_input)}")

    resized = _resize_image(raw, max_dim)
    return base64.b64encode(resized).decode("utf-8")


async def vlm_parse_slide(image_input, port: int = PORT1, prompt_type: str = "default") -> str:
    """
    Send a single image to Ollama VLM for structured text extraction.

    Args:
        image_input: File path (str) or raw PNG bytes.
        port: Ollama API port (default: PORT1 from constants).
        prompt_type: "default", "mermaid", or "retry"

    Returns:
        Extracted Markdown string, or "" on failure.
    """
    try:
        start_time = time.time()
        image_b64 = _encode_image_base64(image_input)

        url = f"{LOCAL_BASE_URL}:{port}/api/generate"
        
        selected_prompt = VLM_EXTRACTION_PROMPT
        if prompt_type == "mermaid":
            selected_prompt = VLM_MERMAID_PROMPT
        elif prompt_type == "retry":
            selected_prompt = VLM_RETRY_PROMPT

        payload = {
            "model": VLM_MODEL,
            "prompt": selected_prompt,
            "images": [image_b64],
            "stream": False,
            "keep_alive": 300,  # Keep model loaded for 5 min between calls
            "options": {
                "temperature": 0.1,  # Low temp for factual extraction
                "num_ctx": 8192,  # More context for complex pages
                "num_predict": 2048,  # Reduced from 4096: most slide content fits in 1000-1500 tokens
            },
        }

        print(f"[VLM] Sending page to Ollama ({VLM_MODEL}) on port {port}...")

        async with httpx.AsyncClient(
            timeout=240
        ) as client:  # 4 min timeout for complex visual pages
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
    prompt_type: str = "default",
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
        prompt_type: "default", "mermaid", or "retry".

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
            print(f"[VLM] Starting {labels[idx]} (prompt: {prompt_type})...")
            result = await vlm_parse_slide(img_bytes, port=port, prompt_type=prompt_type)
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
    print(
        f"[VLM] Concurrent processing complete: {extracted}/{total} pages in {elapsed:.2f}s"
    )
    return final
