import uuid
import os
import shutil
from pathlib import Path
import asyncio
import fitz
import time

from PIL import Image
import io

from app.socket_handler import sio
from app.socket_handler import sio
from core.parsers.image import image_parser
from core.models.document import Document, Page

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

import traceback
# Extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.rtf', '.txt', '.epub', '.odt', '.ppt', '.pptx',
    '.xls', '.xlsx', '.csv', '.html', '.xml', *IMAGE_EXTENSIONS
}

async def extract_document(path, title="Untitled", file_name=None, user_id=None, thread_id=None):
    start_time = time.time()
    file_path = path
    ext = Path(path).suffix.lower()
    name, _ = os.path.splitext(file_name)

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    # --- Handle standalone images ---
    if ext in IMAGE_EXTENSIONS:
        try:
            await sio.emit(f"{user_id}/progress", {"message": f"{title} is an image, extracting text..."})
            text = await image_parser(file_path)
        except Exception as e:
            print(f"Error processing image {file_name}: {str(e)}")
            return None

        doc_id = str(uuid.uuid4())
        await sio.emit(f"{user_id}/progress", {"message": f"processed {file_name} successfully"})
        end_time = time.time()
        print(f"Time taken to process {file_name} main image: {end_time - start_time} seconds")
        return Document(
            id=doc_id,
            type=ext[1:],
            file_name=file_name or os.path.basename(file_path),
            content=[Page(number=1, text=text)],
            title=title,
            full_text=text
        )

    # --- Handle PDFs and other docs ---
    doc = fitz.open(file_path)

    pages = []
    combined_texts = []

    ocr_tasks = {}
    placeholders = {}

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        page_text = page.get_text("text")

        image_names = []
        image_dir = f"data/{user_id}/threads/{thread_id}/images/{name}"
        os.makedirs(image_dir, exist_ok=True)

        # --- Extract embedded raster images ---
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))

            image_name = f"page{page_number + 1}_img{img_index + 1}.{image_ext}"
            image_path = os.path.join(image_dir, image_name)
            image.save(image_path)

            placeholder = f"{{PENDING_{image_name}}}"
            page_text += f"\n\n[Image: {image_name}]\n{placeholder}"
            image_names.append(image_name)

            # Schedule OCR for this image
            ocr_tasks[placeholder] = asyncio.create_task(image_parser(image_path))

        # --- Extract vector diagrams (save as SVG) ---
        svg_name = f"page{page_number + 1}.svg"
        svg_path = os.path.join(image_dir, svg_name)
        try:
            svg = page.get_svg_image()
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg)

            placeholder = f"{{VECTOR_{svg_name}}}"
            page_text += f"\n\n[VectorDiagram: {svg_name}]\n{placeholder}"

            # Optional: also rasterize for OCR fallback
            png_name = f"page{page_number + 1}_vector.png"
            png_path = os.path.join(image_dir, png_name)
            pix = page.get_pixmap(dpi=300)
            pix.save(png_path)
            ocr_tasks[placeholder] = asyncio.create_task(image_parser(png_path))

            image_names.append(svg_name)
            image_names.append(png_name)

        except Exception as e:
            print(f"No vector export available on page {page_number+1}: {e}")

        combined_texts.append(page_text)
        pages.append(Page(number=page_number + 1, text=page_text, images=image_names))

    # --- Wait for all OCR tasks ---
    for placeholder, task in ocr_tasks.items():
        try:
            image_text = await task
        except Exception as e:
            print(f"Error parsing image: {e}")
            image_text = "[Image OCR failed]"

        # Replace placeholders in page + combined text
        for page in pages:
            if placeholder in page.text:
                page.text = page.text.replace(placeholder, image_text, 1)
        combined_texts = [txt.replace(placeholder, image_text, 1) for txt in combined_texts]

    doc_id = str(uuid.uuid4())
    await sio.emit(f"{user_id}/progress", {"message": f"Processing {title} successfully..."})
    end_time = time.time()
    print(f"Time taken to process {title} successfully: {end_time - start_time} seconds")
    return Document(
        id=doc_id,
        type=ext[1:],
        file_name=file_name or os.path.basename(file_path),
        content=pages,
        title=title,
        full_text="\n".join(combined_texts),
    )
