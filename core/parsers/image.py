import asyncio
from PIL import Image
import pytesseract

async def image_parser(image_path: str) -> str:
    def parse():
        image = Image.open(image_path).convert("RGB")
        return pytesseract.image_to_string(image)

    return await asyncio.to_thread(parse)


# also try gemma vision model or some other model maybe. See which is best and faster