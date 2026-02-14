import asyncio
import base64
import time
import aiofiles
import httpx
from PIL import Image
import pytesseract
import easyocr
# from paddleocr import PaddleOCR # Disabled due to dependency conflicts
from core.constants import IMAGE_PARSER_LLM
from core.config import settings
import os
from core.llm.prompts.image_parsing_prompt import image_parsing_prompt

# Optional for Windows if Tesseract throws errors:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

VISION_URL = settings.VISION_URL
MODEL = IMAGE_PARSER_LLM
gemma = settings.USE_VISION_MODEL
REMOTE_GPU = settings.REMOTE_GPU
LOCAL_BASE_URL = settings.LOCAL_BASE_URL
VISION_SERVER_PORT = 11434

_SEMAPHORES: dict[tuple[str, int], asyncio.Semaphore] = {}
_SEMAPHORE_LOCK = asyncio.Lock()
_PADDLEOCR_INSTANCE = None
_PADDLEOCR_LOCK = asyncio.Lock()


async def get_semaphore(port: int, model: str) -> asyncio.Semaphore:
    """Return a shared semaphore for the given model/port pair."""

    key = (model, port)
    semaphore = _SEMAPHORES.get(key)
    if semaphore is not None:
        return semaphore

    async with _SEMAPHORE_LOCK:
        semaphore = _SEMAPHORES.get(key)
        if semaphore is None:
            _SEMAPHORES[key] = asyncio.Semaphore(1)
            semaphore = _SEMAPHORES[key]

    return semaphore


async def image_parser(image_path: str, retries: int = 2) -> str:
    """
    Parse image text using Gemma vision API.

    Sends the image file as multipart/form-data

    Also sends `model` and `port` as query params. Falls back to Tesseract OCR
    if Gemma fails after `retries` attempts. Always returns plain text or an
    empty string if everything fails.
    """

    def tesseract_parse() -> str:
        """Fallback OCR with Tesseract."""
        try:
            image = Image.open(image_path).convert("RGB")
            return pytesseract.image_to_string(image)
        except Exception as e:
            print(f"[Tesseract] Exception: {e}")
            return ""

    async def easyocr_parse() -> str:
        """OCR using EasyOCR - better for tables and general text."""
        try:
            # Run EasyOCR in a thread pool to avoid blocking
            result = await asyncio.to_thread(
                lambda: easyocr.Reader(["en"], gpu=True).readtext(image_path)
            )
            # Extract text maintaining order
            text_lines = [item[1] for item in result]
            return "\n".join(text_lines)
        except Exception as e:
            print(f"[EasyOCR] Exception: {e}")
            return ""

    async def paddleocr_parse() -> str:
        """OCR using PaddleOCR - excellent for flowcharts/diagrams/tables."""
        global _PADDLEOCR_INSTANCE, _PADDLEOCR_LOCK
        try:
            # Use cached PaddleOCR instance to avoid reinitialization
            async with _PADDLEOCR_LOCK:
                if _PADDLEOCR_INSTANCE is None:
                    print("[PaddleOCR] Initializing PaddleOCR instance...")
                    _PADDLEOCR_INSTANCE = await asyncio.to_thread(
                        lambda: PaddleOCR(
                            use_angle_cls=True, lang="en", use_gpu=True, show_log=False
                        )
                    )
                    print("[PaddleOCR] Instance initialized successfully")

            result = await asyncio.to_thread(
                lambda: _PADDLEOCR_INSTANCE.ocr(image_path, cls=True)
            )

            if not result or not result[0]:
                return ""

            text_items = []
            for line in result[0]:
                bbox = line[0]  # Bounding box coordinates
                text = line[1][0]  # Text content
                confidence = line[1][1]  # Confidence score

                # Sort by Y position to maintain top-to-bottom flow
                y_position = bbox[0][1]

                text_items.append(
                    {"text": text, "y": y_position, "confidence": confidence}
                )

            # Sort by Y position to maintain flowchart structure
            text_items.sort(key=lambda x: x["y"])

            # Extract test maintaining order
            text_lines = [item["text"] for item in text_items]
            return "\n".join(text_lines)

        except Exception as e:
            print(f"[PaddleOCR] Exception: {e}")
            return ""

    async def remote_gemma_parse() -> str | None:
        """Try Gemma via remote vision API, return plain text or None."""

        semaphore = await get_semaphore(VISION_SERVER_PORT, MODEL)
        async with semaphore:
            for attempt in range(1, retries + 1):
                try:
                    async with aiofiles.open(image_path, "rb") as f:
                        file_content = await f.read()

                    prompt = image_parsing_prompt()
                    files = {"file": ("filename", file_content)}
                    data = {"prompt": prompt}
                    params = {"model": MODEL, "port": VISION_SERVER_PORT}

                    start_time = time.time()
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            VISION_URL,
                            files=files,
                            data=data,
                            params=params,
                            timeout=60,
                        )
                    end_time = time.time()

                    if response.status_code == 200:
                        payload = response.json()
                        print(
                            f"[Gemma][Remote] succeeded in {end_time - start_time:.2f} seconds"
                        )

                        if isinstance(payload, dict) and "text" in payload:
                            return payload["text"]
                        return str(payload)

                    print(
                        f"[Gemma][Remote] attempt {attempt} failed with status {response.status_code}: {response.text}"
                    )

                except Exception as e:
                    print(f"[Gemma][Remote] attempt {attempt} exception: {e}")

                await asyncio.sleep(1)

        return None

    async def local_vision_parse() -> str | None:
        """Try local Ollama vision endpoint, return plain text or None."""
        semaphore = await get_semaphore(VISION_SERVER_PORT, MODEL)
        async with semaphore:
            for attempt in range(1, retries + 1):
                try:
                    async with aiofiles.open(image_path, "rb") as f:
                        file_content = await f.read()

                    image_b64 = base64.b64encode(file_content).decode("utf-8")
                    prompt = image_parsing_prompt()

                    payload = {
                        "model": MODEL,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                    }

                    start_time = time.time()
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{LOCAL_BASE_URL}:{VISION_SERVER_PORT}/api/generate",
                            json=payload,
                            timeout=60,
                        )
                    end_time = time.time()

                    response.raise_for_status()
                    result = response.json()
                    text = result.get("completion") or result.get("response") or ""

                    print(
                        f"[Gemma][Local] succeeded in {end_time - start_time:.2f} seconds"
                    )
                    return text

                except httpx.HTTPStatusError as e:
                    status = e.response.status_code if e.response else "unknown"
                    body = e.response.text if e.response else ""
                    print(f"[Gemma][Local] attempt {attempt} HTTP {status}: {body}")

                except Exception as e:
                    print(f"[Gemma][Local] attempt {attempt} exception: {e}")

                await asyncio.sleep(1)

        return None

    # ---- Primary Vision Model ----
    if gemma:
        if REMOTE_GPU:
            gemma_result = await remote_gemma_parse()
        else:
            gemma_result = await local_vision_parse()
        if gemma_result:
            return gemma_result.strip()

    # fallback to EasyOCR (better than Tesseract for tables)
    # PaddleOCR disabled due to dependency conflicts
    try:
        if gemma:
            if REMOTE_GPU:
                print(
                    f"Gemma[Remote] failed for {os.path.basename(image_path)}, falling back to EasyOCR"
                )
            else:
                print(
                    f"Gemma[Local] failed for {os.path.basename(image_path)}, falling back to EasyOCR"
                )

        print(f"Processing image: {os.path.basename(image_path)} with EasyOCR")
        easyocr_result = await easyocr_parse()
        if easyocr_result and easyocr_result.strip():
            return easyocr_result.strip()

    except Exception as e:
        print(f"[Fallback EasyOCR] Exception: {e}")

    # final fallback to Tesseract
    try:
        print(
            f"EasyOCR failed or returned empty, falling back to Tesseract for {os.path.basename(image_path)}"
        )
        return (await asyncio.to_thread(tesseract_parse)).strip()
    except Exception as e:
        print(f"[Fallback Tesseract] Fatal exception: {e}")
        return ""
