import asyncio
import time
import aiofiles
import httpx
from PIL import Image
import pytesseract

# Optional for Windows if Tesseract throws errors:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


async def image_parser(image_path: str, retries: int = 3) -> str:

    def tesseract_parse() -> str:
        """Fallback OCR with Tesseract."""
        try:
            image = Image.open(image_path).convert("RGB")
            return pytesseract.image_to_string(image)
        except Exception as e:
            print(f"[Tesseract] Exception: {e}")
            return ""

    try:
        print("processing via tesseract")
        return (await asyncio.to_thread(tesseract_parse)).strip()
    except Exception as e:
        print(f"Fatal exception: {e}")
        return ""
