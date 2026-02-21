import os
import asyncio
import time
from PIL import Image, ImageEnhance
import pytesseract
import easyocr

from core.constants import EASYOCR_WORKERS, TESSERACT_WORKERS, EASYOCR_GPU

# Optional for Windows if Tesseract throws errors:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

_EASYOCR_SEMAPHORE = None
_EASYOCR_SEMAPHORE_LOCK = asyncio.Lock()
_TESSERACT_SEMAPHORE = None
_TESSERACT_SEMAPHORE_LOCK = asyncio.Lock()
_EASYOCR_READER = None
_EASYOCR_READER_LOCK = asyncio.Lock()


async def _get_easyocr_reader():
    """Return a cached EasyOCR Reader instance (avoids reloading ~200MB model)."""
    global _EASYOCR_READER
    if _EASYOCR_READER is not None:
        return _EASYOCR_READER
    async with _EASYOCR_READER_LOCK:
        if _EASYOCR_READER is None:
            _EASYOCR_READER = await asyncio.to_thread(
                lambda: easyocr.Reader(["en"], gpu=EASYOCR_GPU)
            )
    return _EASYOCR_READER


async def get_easyocr_semaphore() -> asyncio.Semaphore:
    global _EASYOCR_SEMAPHORE
    if _EASYOCR_SEMAPHORE is not None:
        return _EASYOCR_SEMAPHORE
    async with _EASYOCR_SEMAPHORE_LOCK:
        if _EASYOCR_SEMAPHORE is None:
            _EASYOCR_SEMAPHORE = asyncio.Semaphore(EASYOCR_WORKERS)
    return _EASYOCR_SEMAPHORE


async def get_tesseract_semaphore() -> asyncio.Semaphore:
    global _TESSERACT_SEMAPHORE
    if _TESSERACT_SEMAPHORE is not None:
        return _TESSERACT_SEMAPHORE
    async with _TESSERACT_SEMAPHORE_LOCK:
        if _TESSERACT_SEMAPHORE is None:
            _TESSERACT_SEMAPHORE = asyncio.Semaphore(TESSERACT_WORKERS)
    return _TESSERACT_SEMAPHORE


async def image_parser(image_path: str) -> str:
    """
    OCR pipeline (no VLM):
    1. Primary: EasyOCR with spatial sorting (bounding-box aware)
    2. Fallback: Tesseract with image preprocessing
    """

    async def easyocr_parse() -> str:
        """OCR using EasyOCR with spatial sorting for tables/flowcharts."""
        try:
            semaphore = await get_easyocr_semaphore()
            async with semaphore:
                reader = await _get_easyocr_reader()
                result = await asyncio.to_thread(
                    lambda: reader.readtext(image_path)
                )

                if not result:
                    return ""

                # Sort by Y-position (top→bottom), then X (left→right)
                # This preserves table row order and flowchart structure
                sorted_results = sorted(
                    result,
                    key=lambda x: (x[0][0][1], x[0][0][0])
                )

                text_lines = [item[1] for item in sorted_results]
                return "\n".join(text_lines)
        except Exception as e:
            print(f"[EasyOCR] Exception: {e}")
            return ""

    async def tesseract_parse() -> str:
        """Fallback OCR with Tesseract + image preprocessing."""
        try:
            semaphore = await get_tesseract_semaphore()
            async with semaphore:

                def _preprocess_and_ocr():
                    img = Image.open(image_path)
                    # Convert to grayscale
                    img = img.convert("L")
                    # Boost contrast
                    img = ImageEnhance.Contrast(img).enhance(2.0)
                    # Binary threshold for cleaner text edges
                    img = img.point(lambda x: 0 if x < 128 else 255)
                    return pytesseract.image_to_string(img)

                return await asyncio.to_thread(_preprocess_and_ocr)
        except Exception as e:
            print(f"[Tesseract] Exception: {e}")
            return ""

    # ---- Primary: EasyOCR ----
    try:
        start_time = time.time()
        print(f"Processing image: {os.path.basename(image_path)} with EasyOCR")
        easyocr_result = await easyocr_parse()
        if easyocr_result and easyocr_result.strip():
            elapsed = time.time() - start_time
            print(f"[EasyOCR] Succeeded in {elapsed:.2f}s for {os.path.basename(image_path)}")
            return easyocr_result.strip()
    except Exception as e:
        print(f"[EasyOCR] Exception: {e}")

    # ---- Fallback: Tesseract ----
    try:
        print(
            f"EasyOCR failed or returned empty, falling back to Tesseract for {os.path.basename(image_path)}"
        )
        start_time = time.time()
        result = (await tesseract_parse()).strip()
        elapsed = time.time() - start_time
        print(f"[Tesseract] Completed in {elapsed:.2f}s for {os.path.basename(image_path)}")
        return result
    except Exception as e:
        print(f"[Tesseract] Fatal exception: {e}")
        return ""
