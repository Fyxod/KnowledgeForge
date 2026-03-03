"""
GLM-OCR Parser Module

Uses Ollama-served GLM-OCR (0.9B) for structured document OCR.
Outputs Markdown with proper tables, formulas, and layout preservation.

GLM-OCR achieves 94.62 on OmniDocBench V1.5 (#1 overall).
Architecture: CogViT encoder + PP-DocLayout-V3 + GLM-0.5B decoder.

Follows the project's async httpx pattern (see core/parsers/vlm.py).
"""

import asyncio
import base64
import io
import os
import time
import traceback

import httpx
from PIL import Image

from core.config import settings
from core.constants import PORT1, GLM_OCR_MODEL, GLM_OCR_WORKERS

LOCAL_BASE_URL = settings.LOCAL_BASE_URL

# Prompts matching GLM-OCR's expected format
GLM_OCR_TEXT_PROMPT = "Text Recognition:"
GLM_OCR_TABLE_PROMPT = "Table Recognition:"
GLM_OCR_FIGURE_PROMPT = "Figure Recognition:"

# Max image dimension — GLM-OCR handles higher res than the VLM
GLM_OCR_MAX_IMAGE_DIM = 2048

# Concurrency controls (lazy-init singletons)
_GLM_OCR_SEMAPHORE = None
_GLM_OCR_SEMAPHORE_LOCK = asyncio.Lock()


async def _get_semaphore() -> asyncio.Semaphore:
    """Lazy-init semaphore for concurrency limiting."""
    global _GLM_OCR_SEMAPHORE
    if _GLM_OCR_SEMAPHORE is not None:
        return _GLM_OCR_SEMAPHORE
    async with _GLM_OCR_SEMAPHORE_LOCK:
        if _GLM_OCR_SEMAPHORE is None:
            _GLM_OCR_SEMAPHORE = asyncio.Semaphore(GLM_OCR_WORKERS)
    return _GLM_OCR_SEMAPHORE


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
    print(f"[GLM-OCR] Resized image {w}x{h} → {new_w}x{new_h} (max_dim={max_dim})")
    return buf.getvalue()


def _encode_image_base64(
    image_input, max_dim: int = GLM_OCR_MAX_IMAGE_DIM
) -> str:
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


async def glm_ocr_parse(
    image_input,
    mode: str = "text",
    port: int = PORT1,
) -> str:
    """
    Run GLM-OCR on a single image via Ollama.

    Args:
        image_input: File path (str) or raw PNG bytes.
        mode: Recognition mode — "text", "table", or "figure".
        port: Ollama API port (default: PORT1 from constants).

    Returns:
        Extracted Markdown string, or "" on failure.
    """
    prompts = {
        "text": GLM_OCR_TEXT_PROMPT,
        "table": GLM_OCR_TABLE_PROMPT,
        "figure": GLM_OCR_FIGURE_PROMPT,
    }
    prompt = prompts.get(mode, GLM_OCR_TEXT_PROMPT)

    try:
        start_time = time.time()
        image_b64 = _encode_image_base64(image_input)

        semaphore = await _get_semaphore()
        async with semaphore:
            url = f"{LOCAL_BASE_URL}:{port}/api/generate"

            payload = {
                "model": GLM_OCR_MODEL,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "keep_alive": 300,  # Keep model loaded for 5 min between calls
                "options": {
                    "temperature": 0.01,  # Near-deterministic for factual extraction
                    "num_ctx": 8192,
                    "num_predict": 4096,
                },
            }

            label = (
                os.path.basename(image_input)
                if isinstance(image_input, str)
                else "bytes"
            )
            print(
                f"[GLM-OCR] Sending {label} to Ollama ({GLM_OCR_MODEL}) port {port} mode={mode}..."
            )

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            result = response.json()
            content = result.get("response", "").strip()

            elapsed = time.time() - start_time
            print(
                f"[GLM-OCR] Completed in {elapsed:.2f}s | {len(content)} chars extracted."
            )

            return content

    except httpx.ConnectError:
        print(
            f"[GLM-OCR] Connection refused at {LOCAL_BASE_URL}:{port}. "
            "Is Ollama running with glm-ocr model? Try: ollama pull glm-ocr:q8_0"
        )
        return ""
    except httpx.TimeoutException:
        print(f"[GLM-OCR] Request timed out after 120s for model {GLM_OCR_MODEL}.")
        return ""
    except httpx.HTTPStatusError as e:
        print(f"[GLM-OCR] HTTP error: {e}")
        return ""
    except Exception as e:
        print(f"[GLM-OCR] Unexpected error: {e}")
        traceback.print_exc()
        return ""


async def glm_ocr_parse_concurrent(
    images: list,
    page_labels: list[str] | None = None,
    mode: str = "text",
    port: int = PORT1,
    max_concurrent: int = 3,
) -> list[str]:
    """
    Process multiple images concurrently using async single-image GLM-OCR calls.

    Args:
        images: List of file paths (str) or raw bytes, one per page/image.
        page_labels: Optional labels for logging (e.g. ["Page 1", "Slide 3"]).
        mode: Recognition mode — "text", "table", or "figure".
        port: Ollama API port.
        max_concurrent: Max simultaneous GLM-OCR calls.

    Returns:
        List of extracted Markdown strings, one per input image.
        Empty string for images where extraction failed.
    """
    if not images:
        return []

    total = len(images)
    labels = page_labels or [f"Page {i + 1}" for i in range(total)]
    semaphore = asyncio.Semaphore(max_concurrent)

    print(
        f"[GLM-OCR] Concurrent processing: {total} images, max {max_concurrent} at a time"
    )
    overall_start = time.time()

    async def _process_one(idx: int, img_input) -> str:
        async with semaphore:
            print(f"[GLM-OCR] Starting {labels[idx]}...")
            result = await glm_ocr_parse(img_input, mode=mode, port=port)
            if result:
                print(f"[GLM-OCR] {labels[idx]} done ({len(result)} chars)")
            else:
                print(f"[GLM-OCR] {labels[idx]} returned empty")
            return result

    # Launch all tasks, semaphore limits concurrency
    tasks = [_process_one(i, img) for i, img in enumerate(images)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to empty strings
    final = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"[GLM-OCR] {labels[i]} failed with error: {r}")
            final.append("")
        else:
            final.append(r or "")

    elapsed = time.time() - overall_start
    extracted = sum(1 for r in final if r)
    print(
        f"[GLM-OCR] Concurrent processing complete: {extracted}/{total} images in {elapsed:.2f}s"
    )
    return final
