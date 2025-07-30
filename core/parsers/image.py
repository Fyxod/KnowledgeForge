import asyncio
from PIL import Image
import pytesseract

# for windows if not wokring explicitly set the tesseract_cmd
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


async def image_parser(image_path: str) -> str:
    def parse():
        image = Image.open(image_path).convert("RGB")
        return pytesseract.image_to_string(image)

    return await asyncio.to_thread(parse)


# also try gemma vision model or some other model maybe. See which is best and faster