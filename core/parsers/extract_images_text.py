# import os
# import asyncio
# from typing import List
# from core.parsers.image_test import image_parser
# import time

# # Helper to get all image paths from a folder (recursively)
# def get_all_image_paths(folder: str) -> List[str]:
#     image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"}
#     image_paths = []
#     for root, _, files in os.walk(folder):
#         for file in files:
#             ext = os.path.splitext(file)[1].lower()
#             if ext in image_exts:
#                 image_paths.append(os.path.join(root, file))
#     return image_paths


# async def extract_text_from_images_folder(folder: str, batch_size: int = 100):
#     image_paths = get_all_image_paths(folder)
#     print(f"Found {len(image_paths)} images in {folder}")
#     results = {}
#     for i in range(0, len(image_paths), batch_size):
#         batch = image_paths[i : i + batch_size]
#         b_s = time.time()
#         batch_results = await asyncio.gather(
#             *(image_parser(img_path) for img_path in batch)
#         )
#         for img_path, text in zip(batch, batch_results):
#             results[img_path] = text
#         b_e = time.time()
#         print(f"Processed batch {i//batch_size + 1}: {len(batch)} images in {b_e - b_s} seconds")
#     return results


# s = time.time()
# asyncio.run(extract_text_from_images_folder("images"))
# e = time.time()
# print(f"Total time taken: {e - s} seconds")
