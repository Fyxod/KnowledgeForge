import asyncio
import time
import requests
import aiofiles
import httpx
from PIL import Image
import pytesseract
from core.constants import IMAGE_PARSER_LLM
# Optional for Windows:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

URL = "https://llm.katiar.xyz/vision-query"
MODEL = IMAGE_PARSER_LLM
# gemma=True

async def image_parser(image_path: str, retries: int = 3) -> str:
    """
    Parse image text using Gemma vision API.
    Falls back to Tesseract OCR if Gemma fails after `retries` attempts.
    Always returns plain text.
    """

    def tesseract_parse() -> str:
        """Fallback OCR with Tesseract."""
        image = Image.open(image_path).convert("RGB")
        return pytesseract.image_to_string(image)

    async def gemma_parse() -> str | None:
        """Try Gemma vision API with retries, return plain text."""
        for attempt in range(1, retries + 1):
            try:
                start = time.time()

                async with aiofiles.open(image_path, "rb") as f:
                    file_content = await f.read()

                files = {"file": ("filename", file_content)}
                params = {"model": MODEL}

                async with httpx.AsyncClient() as client:
                    response = await client.post(URL, files=files, params=params)
                
                end = time.time()
                print(f"[Gemma attempt {attempt}] Time taken: {end - start:.2f} seconds")

                if response.status_code == 200:
                    data = response.json()
                        
                    if isinstance(data, dict) and "text" in data:
                        return data["text"]
                    return str(data) 

                print(f"[Gemma attempt {attempt}] Failed with status {response.status_code}: {response.text}")

            except Exception as e:
                print(f"[Gemma attempt {attempt}] Exception: {e}")
                print(e)
            await asyncio.sleep(1)

        return None

    gemma_result = None
    # gemma_result = await gemma_parse()
    if gemma_result:
        return gemma_result.strip()

    # fallback to Tesseract
    print("[Fallback] Using Tesseract OCR")
    return (await asyncio.to_thread(tesseract_parse)).strip()


