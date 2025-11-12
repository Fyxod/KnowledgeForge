import asyncio
import time
import aiofiles
import httpx
from PIL import Image
import pytesseract
from core.constants import IMAGE_PARSER_LLM
from core.config import settings
import os
from core.llm.prompts.image_parsing_prompt import image_parsing_prompt

# Optional for Windows if Tesseract throws errors:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

VISION_URL = settings.VISION_URL
MODEL = IMAGE_PARSER_LLM
gemma = settings.USE_VISION_MODEL


async def image_parser(image_path: str, retries: int = 3) -> str:
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

    async def gemma_parse() -> str | None:
        """Try Gemma vision API with retries, return plain text or None."""
        for attempt in range(1, retries + 1):
            try:

                async with aiofiles.open(image_path, "rb") as f:
                    file_content = await f.read()

                prompt = image_parsing_prompt()
                files = {"file": ("filename", file_content)}
                data = {"prompt": prompt}
                params = {"model": MODEL, "port": 11434}

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        VISION_URL, files=files, data=data, params=params, timeout=300
                    )

                if response.status_code == 200:
                    data = response.json()

                    if isinstance(data, dict) and "text" in data:
                        return data["text"]
                    return str(data)

                print(
                    f"[Gemma attempt {attempt}] Failed with status {response.status_code}: {response.text}"
                )

            except Exception as e:
                print(f"[Gemma attempt {attempt}] Exception: {e}")

            await asyncio.sleep(1)

        return None

    if gemma:
        start_time = time.time()
        gemma_result = await gemma_parse()
        end_time = time.time()
        if gemma_result:
            print(f"Gemma succeeded in {end_time - start_time:.2f} seconds")
            return gemma_result.strip()

    # fallback to Tesseract
    try:
        if gemma:
            print(
                f"Gemma failed for {os.path.basename(image_path)}, falling back to Tesseract"
            )
        print(f"processing image: {os.path.basename(image_path)} with Tesseract")
        return (await asyncio.to_thread(tesseract_parse)).strip()
    except Exception as e:
        print(f"[Fallback Tesseract] Fatal exception: {e}")
        return ""
