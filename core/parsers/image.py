import asyncio
from PIL import Image
import pytesseract
from core.config import settings

# Optional for Windows if Tesseract throws errors:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


async def image_parser(image_path: str) -> str:

    def tesseract_parse() -> str:
        """OCR with Tesseract."""
        try:
            image = Image.open(image_path).convert("RGB")
            return pytesseract.image_to_string(image)
        except Exception as e:
            print(f"[Tesseract] Exception: {e}")
            return ""

    try:
        return (await asyncio.to_thread(tesseract_parse)).strip()
    except Exception as e:
        print(f"Fatal exception: {e}")
        return ""
