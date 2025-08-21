# import os
# from core.config import settings
# from google import genai
# import asyncio
# import time
# import sys

# sys.setrecursionlimit(5000)

# API_KEYS = [
#     settings.GOOGLE_API_KEY_1,
#     settings.GOOGLE_API_KEY_2,
#     settings.GOOGLE_API_KEY_3,
#     settings.GOOGLE_API_KEY_4,
#     settings.GOOGLE_API_KEY_5,
#     settings.GOOGLE_API_KEY_6,
#     settings.GOOGLE_API_KEY_7,
#     settings.GOOGLE_API_KEY_8,
#     settings.GOOGLE_API_KEY_9,
#     settings.GOOGLE_API_KEY_10,
#     settings.GOOGLE_API_KEY_11,
#     settings.GOOGLE_API_KEY_12,
#     settings.GOOGLE_API_KEY_13
# ]

# count = 0
# image_prompt = "Extract all text from this image. Return only the text, exactly as it appears, with nothing else."

# async def image_parser(image_path: str, prompt: str = image_prompt, model: str = "gemini-2.0-flash-lite"):
#     global count

#     if not os.path.exists(image_path):
#         print(f"Image file not found: {image_path}")
#         return
    
#     with open(image_path, 'rb') as f:
#         image_bytes = f.read()
        
#     for _ in range(len(API_KEYS) * 3):
#         api_key = API_KEYS[count % len(API_KEYS)]
#         client = genai.Client(api_key=api_key)
#         count = (count + 1) % len(API_KEYS)
        
#         try:
#             print("before the image parser")
#             start = time.time()
#             response = await asyncio.to_thread(
#                 client.models.generate_content,
#                 model=model,
#                 contents=[
#                     genai.types.Part.from_bytes(
#                         data=image_bytes,
#                         mime_type='image/png',
#                     ),
#                     prompt
#                 ]
#             )
#             end = time.time()
#             print(response.text)
#             print(f"Image parsing took {end - start} seconds")
#             return response.text

#         except Exception as e:
#             print(f"LLM invocation failed with key {count}: {e}")
#             count = (count + 1) % len(API_KEYS)
#             await asyncio.sleep(2)

#     raise RuntimeError("All API keys exhausted or rate-limited.")
