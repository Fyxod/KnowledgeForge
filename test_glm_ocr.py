"""
Standalone GLM-OCR Test Script
==============================

Tests GLM-OCR via Ollama's /api/generate endpoint.
Completely independent of the PRISM codebase — uses only httpx + Pillow + PyMuPDF.

Diagnoses common issues:
  - Connection failures
  - Timeout / client disconnect ("aborting completion")
  - Empty response
  - Model not found

Usage:
  python test_glm_ocr.py                                          # Quick connectivity test
  python test_glm_ocr.py --image /path/to/document.pdf            # OCR page 1 of PDF
  python test_glm_ocr.py --image /path/to/document.pdf --page 3   # OCR page 3 of PDF
  python test_glm_ocr.py --image /path/to/img.png                 # OCR a standalone image
  python test_glm_ocr.py --image /path/to/img.png --mode table    # Table recognition
  python test_glm_ocr.py --image /path/to/img.png --no-stream     # Test non-streaming

Requirements:
  pip install httpx Pillow PyMuPDF  (all already in PRISM's requirements)
"""

import argparse
import asyncio
import base64
import io
import json
import os
import sys
import time

import httpx
from PIL import Image

# ─── Configuration ───────────────────────────────────────────────────────────
OLLAMA_HOST = "http://localhost"
OLLAMA_PORT = 11434
MODEL_NAME = "glm-ocr:latest"  # Change if using a custom Modelfile variant

# Prompts per GLM-OCR documentation
PROMPTS = {
    "text": "Text Recognition:",
    "table": "Table Recognition:",
    "figure": "Figure Recognition:",
}

# Image resize
MAX_IMAGE_DIM = 2048


# ─── Helpers ─────────────────────────────────────────────────────────────────
def pdf_to_image(pdf_path: str, page_num: int = 1, dpi: int = 150) -> bytes:
    """Render a PDF page to PNG bytes using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"  PDF has {total_pages} page(s)")

    if page_num < 1 or page_num > total_pages:
        print(f"  ✗ Page {page_num} out of range (1-{total_pages})")
        doc.close()
        return None

    page = doc.load_page(page_num - 1)  # 0-indexed
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    print(f"  Rendered page {page_num} at {dpi} DPI: {pix.width}x{pix.height} ({len(png_bytes):,} bytes)")
    doc.close()
    return png_bytes


def prepare_image(image_input, max_dim: int = MAX_IMAGE_DIM) -> str:
    """Prepare image bytes or file to base64-encoded PNG, resizing if needed."""
    if isinstance(image_input, bytes):
        raw = image_input
    else:
        with open(image_input, "rb") as f:
            raw = f.read()

    img = Image.open(io.BytesIO(raw))
    w, h = img.size
    print(f"  Image dimensions: {w}x{h} ({len(raw):,} bytes)")

    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"  Resized to: {new_w}x{new_h}")
    else:
        print(f"  No resize needed (within {max_dim}px)")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    print(f"  PNG size: {len(png_bytes):,} bytes")

    b64 = base64.b64encode(png_bytes).decode("utf-8")
    print(f"  Base64 length: {len(b64):,} chars")
    return b64


# ─── Test 1: Connectivity ───────────────────────────────────────────────────
async def test_connectivity(host: str, port: int):
    """Check if Ollama is reachable and list models."""
    print("\n" + "=" * 60)
    print("TEST 1: Ollama Connectivity")
    print("=" * 60)

    url = f"{host}:{port}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        models = data.get("models", [])
        print(f"  ✓ Ollama is reachable at {host}:{port}")
        print(f"  ✓ {len(models)} model(s) installed:")
        for m in models:
            name = m.get("name", "?")
            size_gb = m.get("size", 0) / (1024**3)
            print(f"    - {name} ({size_gb:.1f} GB)")

        # Check if glm-ocr is installed
        model_names = [m.get("name", "") for m in models]
        if any("glm-ocr" in n for n in model_names):
            print(f"  ✓ GLM-OCR model found!")
        else:
            print(f"  ✗ GLM-OCR model NOT found. Run: ollama pull glm-ocr:latest")
            return False
        return True

    except httpx.ConnectError:
        print(f"  ✗ Cannot connect to Ollama at {host}:{port}")
        print(f"    Is Ollama running? Try: ollama serve")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


# ─── Test 2: Text-only prompt (no image) ────────────────────────────────────
async def test_text_only(host: str, port: int, model: str):
    """Send a simple text prompt to verify the model loads and responds."""
    print("\n" + "=" * 60)
    print("TEST 2: Text-Only Prompt (model load test)")
    print("=" * 60)

    url = f"{host}:{port}/api/generate"
    payload = {
        "model": model,
        "prompt": "Hello",
        "stream": False,
        "options": {
            "num_ctx": 8192,
            "num_predict": 64,
            "temperature": 0,
        },
    }

    print(f"  Sending text-only prompt to {model}...")
    print(f"  (This may take 30-60s if the model needs to load)")

    start = time.time()
    try:
        # Long timeout for first-time model load
        timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

        elapsed = time.time() - start
        data = resp.json()
        response_text = data.get("response", "")
        total_dur = data.get("total_duration", 0) / 1e9  # nanoseconds -> seconds
        load_dur = data.get("load_duration", 0) / 1e9
        eval_count = data.get("eval_count", 0)

        print(f"  ✓ Response received in {elapsed:.1f}s")
        print(f"  ✓ Model load time: {load_dur:.1f}s")
        print(f"  ✓ Total Ollama duration: {total_dur:.1f}s")
        print(f"  ✓ Tokens generated: {eval_count}")
        print(f"  ✓ Response: {response_text[:200]}")
        return True

    except httpx.TimeoutException:
        elapsed = time.time() - start
        print(f"  ✗ Timed out after {elapsed:.1f}s")
        print(f"    The model may need more time to load.")
        return False
    except httpx.HTTPStatusError as e:
        print(f"  ✗ HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


# ─── Test 3: Image OCR with STREAMING ───────────────────────────────────────
async def test_streaming_ocr(host: str, port: int, model: str, image_b64: str, mode: str):
    """Test GLM-OCR with streaming enabled — the recommended approach."""
    print("\n" + "=" * 60)
    print(f"TEST 3: Streaming OCR (mode={mode})")
    print("=" * 60)

    url = f"{host}:{port}/api/generate"
    prompt = PROMPTS.get(mode, PROMPTS["text"])

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": True,  # Stream token by token
        "keep_alive": 300,
        "options": {
            "num_ctx": 8192,
            "num_predict": 4096,
            "temperature": 0,
        },
    }

    print(f"  Prompt: {prompt}")
    print(f"  Streaming: True")
    print(f"  num_ctx: 8192, num_predict: 4096  (4096 is too small — known Ollama bug)")
    print(f"  Sending request...")

    start = time.time()
    full_response = ""
    token_count = 0
    first_token_time = None

    try:
        # IMPORTANT: separate timeouts — long read timeout for streaming
        timeout = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    token = chunk.get("response", "")
                    if token:
                        if first_token_time is None:
                            first_token_time = time.time() - start
                            print(f"  ✓ First token at {first_token_time:.1f}s")
                        full_response += token
                        token_count += 1
                        # Print progress every 50 tokens
                        if token_count % 50 == 0:
                            print(f"    ... {token_count} tokens received ({time.time() - start:.1f}s)")

                    if chunk.get("done", False):
                        # Extract timing stats from final chunk
                        total_dur = chunk.get("total_duration", 0) / 1e9
                        load_dur = chunk.get("load_duration", 0) / 1e9
                        eval_count = chunk.get("eval_count", 0)
                        prompt_eval = chunk.get("prompt_eval_count", 0)
                        break

        elapsed = time.time() - start

        print(f"\n  {'=' * 40}")
        print(f"  RESULTS:")
        print(f"  {'=' * 40}")
        print(f"  ✓ Total time: {elapsed:.1f}s")
        print(f"  ✓ Time to first token: {first_token_time:.1f}s" if first_token_time else "  ✗ No tokens received")
        print(f"  ✓ Tokens generated: {token_count}")
        print(f"  ✓ Response length: {len(full_response)} chars")
        if load_dur:
            print(f"  ✓ Model load time: {load_dur:.1f}s")
        if total_dur:
            print(f"  ✓ Ollama total duration: {total_dur:.1f}s")
        if prompt_eval:
            print(f"  ✓ Prompt tokens processed: {prompt_eval}")

        if full_response.strip():
            print(f"\n  ✓ OCR Output Preview (first 500 chars):")
            print(f"  {'─' * 40}")
            for line in full_response.strip()[:500].split("\n"):
                print(f"  │ {line}")
            print(f"  {'─' * 40}")
            return True
        else:
            print(f"\n  ✗ Response is EMPTY!")
            print(f"    This may indicate the model cannot process this image type.")
            return False

    except httpx.TimeoutException:
        elapsed = time.time() - start
        print(f"  ✗ Timed out after {elapsed:.1f}s")
        print(f"    Tokens received so far: {token_count}")
        if full_response:
            print(f"    Partial response ({len(full_response)} chars):")
            print(f"    {full_response[:200]}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


# ─── Test 4: Image OCR NON-STREAMING (for comparison) ───────────────────────
async def test_non_streaming_ocr(host: str, port: int, model: str, image_b64: str, mode: str):
    """Test GLM-OCR without streaming — may timeout on large images."""
    print("\n" + "=" * 60)
    print(f"TEST 4: Non-Streaming OCR (mode={mode}) — for comparison")
    print("=" * 60)

    url = f"{host}:{port}/api/generate"
    prompt = PROMPTS.get(mode, PROMPTS["text"])

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "keep_alive": 300,
        "options": {
            "num_ctx": 8192,
            "num_predict": 4096,
            "temperature": 0,
        },
    }

    print(f"  Prompt: {prompt}")
    print(f"  Streaming: False (waiting for full response)")
    print(f"  Timeout: 600s")
    print(f"  Sending request...")

    start = time.time()
    try:
        timeout = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

        elapsed = time.time() - start
        data = resp.json()
        response_text = data.get("response", "").strip()
        total_dur = data.get("total_duration", 0) / 1e9
        load_dur = data.get("load_duration", 0) / 1e9
        eval_count = data.get("eval_count", 0)

        print(f"  ✓ Response received in {elapsed:.1f}s")
        print(f"  ✓ Model load: {load_dur:.1f}s | Total: {total_dur:.1f}s")
        print(f"  ✓ Tokens: {eval_count} | Chars: {len(response_text)}")

        if response_text:
            print(f"\n  ✓ OCR Output Preview:")
            print(f"  {'─' * 40}")
            for line in response_text[:500].split("\n"):
                print(f"  │ {line}")
            print(f"  {'─' * 40}")
            return True
        else:
            print(f"  ✗ Response is EMPTY!")
            return False

    except httpx.TimeoutException:
        elapsed = time.time() - start
        print(f"  ✗ Timed out after {elapsed:.1f}s")
        print(f"    THIS is likely the 'aborting completion' issue!")
        print(f"    Solution: use streaming mode (Test 3)")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Test GLM-OCR via Ollama")
    parser.add_argument("--image", type=str, help="Path to test file (PNG/JPG/PDF)")
    parser.add_argument("--page", type=int, default=1,
                       help="PDF page number to test (default: 1)")
    parser.add_argument("--mode", type=str, default="text",
                       choices=["text", "table", "figure"],
                       help="OCR mode (default: text)")
    parser.add_argument("--host", type=str, default=OLLAMA_HOST,
                       help=f"Ollama host (default: {OLLAMA_HOST})")
    parser.add_argument("--port", type=int, default=OLLAMA_PORT,
                       help=f"Ollama port (default: {OLLAMA_PORT})")
    parser.add_argument("--model", type=str, default=MODEL_NAME,
                       help=f"Model name (default: {MODEL_NAME})")
    parser.add_argument("--no-stream", action="store_true",
                       help="Also run non-streaming test for comparison")
    args = parser.parse_args()

    print("=" * 60)
    print("  GLM-OCR Diagnostic Test Suite")
    print(f"  Host: {args.host}:{args.port}")
    print(f"  Model: {args.model}")
    print("=" * 60)

    results = {}

    # Test 1: Connectivity
    results["connectivity"] = await test_connectivity(args.host, args.port)
    if not results["connectivity"]:
        print("\n✗ Cannot proceed — Ollama is not reachable.")
        sys.exit(1)

    # Test 2: Text-only (model load)
    results["text_only"] = await test_text_only(args.host, args.port, args.model)

    # Test 3 & 4: OCR (if file provided)
    if args.image:
        if not os.path.exists(args.image):
            print(f"\n✗ File not found: {args.image}")
            sys.exit(1)

        file_ext = os.path.splitext(args.image)[1].lower()
        print(f"\nPreparing input: {args.image}")

        # PDF: render the specified page to an image first
        if file_ext == ".pdf":
            print(f"  Detected PDF — rendering page {args.page} at 150 DPI...")
            png_bytes = pdf_to_image(args.image, page_num=args.page, dpi=150)
            if png_bytes is None:
                print("\n✗ Failed to render PDF page.")
                sys.exit(1)
            image_b64 = prepare_image(png_bytes)
        else:
            # Standard image file (PNG, JPG, etc.)
            image_b64 = prepare_image(args.image)

        # Test 3: Streaming (recommended)
        results["streaming_ocr"] = await test_streaming_ocr(
            args.host, args.port, args.model, image_b64, args.mode
        )

        # Test 4: Non-streaming (optional, for comparison)
        if args.no_stream:
            results["non_streaming_ocr"] = await test_non_streaming_ocr(
                args.host, args.port, args.model, image_b64, args.mode
            )
    else:
        print("\n⚠ No file provided. Skipping OCR tests.")
        print("  Use: python test_glm_ocr.py --image /path/to/document.pdf")
        print("  Or:  python test_glm_ocr.py --image /path/to/image.png")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} — {test_name}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
