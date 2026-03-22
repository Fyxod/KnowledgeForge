"""
VLM (Visual Language Model) Parser Module

Uses a vLLM-hosted multimodal model (e.g., Qwen/Qwen2-VL-7B-Instruct-AWQ) via its
OpenAI-compatible API to extract structured text from presentation slides, complex
PDF pages, and other visually-rich documents that standard OCR misses.

Replaces the previous Ollama /api/generate HTTP calls with AsyncOpenAI targeting
settings.VLLM_VLM_URL. The `port` parameter is kept on the public API for backward
compatibility but is no longer used — the endpoint URL comes from config.
"""

import asyncio
import base64
import io
import time
import traceback

from openai import AsyncOpenAI
from PIL import Image

from core.config import settings
from core.constants import PORT1, VLM_MODEL

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


async def vlm_parse_slide(
    image_input,
    port: int = PORT1,
    prompt_type: str = "default",
    custom_prompt: str | None = None,
    _is_retry: bool = False,
) -> str:
    """
    Send a single image to the vLLM VLM for structured text extraction.

    Args:
        image_input: File path (str) or raw PNG bytes.
        port: Kept for backward compatibility — ignored. vLLM URL comes from
              settings.VLLM_VLM_URL.
        prompt_type: "default", "mermaid", or "retry". Ignored when custom_prompt is set.
        custom_prompt: If provided, overrides prompt_type and sends this exact prompt.
            Use for query-time VLM where the user's question is the prompt.
        _is_retry: Internal flag — when True, uses VLM_RETRY_IMAGE_DIM and VLM_RETRY_PROMPT.

    Returns:
        Extracted Markdown string, or "" on failure.
    """
    try:
        start_time = time.time()

        max_dim = VLM_RETRY_IMAGE_DIM if _is_retry else VLM_MAX_IMAGE_DIM
        image_b64 = _encode_image_base64(image_input, max_dim=max_dim)

        if custom_prompt:
            selected_prompt = custom_prompt
        elif prompt_type == "mermaid":
            selected_prompt = VLM_MERMAID_PROMPT
        elif prompt_type == "retry" or _is_retry:
            selected_prompt = VLM_RETRY_PROMPT
        else:
            selected_prompt = VLM_EXTRACTION_PROMPT

        vlm_url = settings.effective_vlm_url
        vlm_model = settings.effective_vlm_model
        print(f"[VLM] Sending page to vLLM ({vlm_model}) at {vlm_url} ...")

        # Disable thinking for OCR/image tasks — reasoning chains waste time on structured
        # extraction. Server-side --reasoning-parser qwen3 also strips them, but this
        # ensures Qwen doesn't generate them at all (faster, fewer tokens billed).
        # No-op for gpt-oss-20b (different chat template, parameter silently ignored).
        extra_body: dict | None = None
        if "qwen" in vlm_model.lower():
            extra_body = {"chat_template_kwargs": {"enable_thinking": False}}

        client = AsyncOpenAI(base_url=vlm_url, api_key="EMPTY")
        response = await client.chat.completions.create(
            model=vlm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                        {"type": "text", "text": selected_prompt},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=2048,
            extra_body=extra_body,
        )

        content = (response.choices[0].message.content or "").strip()

        elapsed = time.time() - start_time
        print(f"[VLM] Completed in {elapsed:.2f}s  |  {len(content)} chars extracted.")

        return content

    except Exception as e:
        vllm_url = settings.effective_vlm_url
        if "connect" in str(e).lower() or "connection" in str(e).lower():
            print(
                f"[VLM] Connection refused at {vllm_url}. "
                "Is the vLLM VLM instance running? Try: bash scripts/start_vllm.sh"
            )
        elif "timeout" in str(e).lower():
            print(f"[VLM] Request timed out for model {settings.effective_vlm_model}.")
        else:
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
        port: Kept for backward compatibility — ignored. vLLM URL comes from config.
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
