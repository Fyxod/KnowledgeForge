import asyncio
import time
import httpx
import aiofiles
import os
import base64
import openai
from PIL import Image
import pytesseract
from core.constants import IMAGE_PARSER_LLM
from core.config import settings

client = openai.AsyncOpenAI(api_key=settings.VISION_API)
OPENAI_MODEL = "gpt-4o-mini"

GEMMA_URL = "https://llm.katiyar.xyz/vision-query"
GEMMA_MODEL = IMAGE_PARSER_LLM

async def image_parser(image_path: str) -> str:
    """
    Parse image text using a fallback chain: OpenAI -> Gemma -> Tesseract.
    Always returns plain text.
    """

    def tesseract_parse() -> str:
        """Fallback OCR with Tesseract."""
        image = Image.open(image_path).convert("RGB")
        return pytesseract.image_to_string(image)

    async def openai_parse(retries: int = 2) -> str | None:
        """Try OpenAI vision API with retries, return plain text."""
        prompt = "Extract all visible text from the image. Then provide a concise description of the visual content of the image itself. Combine both so the output fully represents what is in the image."

        for attempt in range(1, retries + 1):
            try:
                start = time.time()

                async with aiofiles.open(image_path, "rb") as f:
                    image_data = await f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                response = await client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                )
                
                end = time.time()
                print(f"[VISION attempt {attempt}] Time taken: {end - start:.2f} seconds")

                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
                
                print(f"[VISION attempt {attempt}] Failed: Empty response from API.")

            except Exception as e:
                print(f"[VISION attempt {attempt}] failed")

            if attempt < retries:
                await asyncio.sleep(0.1) # Wait before retrying

        return None

    async def gemma_parse(retries: int = 3) -> str | None:
        """Try Gemma vision API with retries, return plain text."""
        for attempt in range(1, retries + 1):
            try:
                start = time.time()

                async with aiofiles.open(image_path, "rb") as f:
                    file_content = await f.read()

                files = {"file": ("filename", file_content)}
                params = {"model": GEMMA_MODEL}

                async with httpx.AsyncClient() as client:
                    response = await client.post(GEMMA_URL, files=files, params=params)
                
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

            if attempt < retries:
                await asyncio.sleep(0.1)

        return None

    # 1. Try OpenAI first
    openai_result = await openai_parse()
    if openai_result:
        return openai_result.strip()

    # 2. Fallback to Gemma
    print("[Fallback] VISION failed, trying Gemma...")
    gemma_result = await gemma_parse()
    if gemma_result:
        return gemma_result.strip()

    # 3. Final fallback to Tesseract
    print("[Fallback] Gemma also failed, using Tesseract OCR")
    return (await asyncio.to_thread(tesseract_parse)).strip()