import pandas as pd
import uuid
import os
import shutil
from pathlib import Path
import asyncio
import fitz
import time
import markdown
from bs4 import BeautifulSoup
from PIL import Image
import io
import re
from app.socket_handler import sio
from core.parsers.image import image_parser
from core.models.document import Document, Page

from pptx import Presentation

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

import traceback

# Extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"}
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".rtf",
    ".txt",
    ".epub",
    ".odt",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".csv",
    ".html",
    ".xml",
    ".md",
    *IMAGE_EXTENSIONS,
}


async def extract_document(
    path, title="Untitled", file_name=None, user_id=None, thread_id=None
):
    start_time = time.time()
    file_path = path
    ext = Path(path).suffix.lower()
    name, _ = os.path.splitext(file_name)

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    # --- Handle standalone images ---
    if ext in IMAGE_EXTENSIONS:
        try:
            await sio.emit(
                f"{user_id}/progress",
                {"message": f"{title} is an image, extracting text..."},
            )
            text = await image_parser(file_path)
        except Exception as e:
            print(f"Error processing image {file_name}: {str(e)}")
            return None

        doc_id = str(uuid.uuid4())
        await sio.emit(
            f"{user_id}/progress", {"message": f"processed {file_name} successfully"}
        )
        end_time = time.time()
        print(
            f"Time taken to process {file_name} main image: {end_time - start_time} seconds"
        )
        return Document(
            id=doc_id,
            type=ext[1:],
            file_name=file_name or os.path.basename(file_path),
            content=[Page(number=1, text=text)],
            title=title,
            full_text=text,
        )

    # --- Handle Markdown files ---
    if ext == ".md":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md_text = f.read()

            # Convert markdown -> HTML -> plain text
            html = markdown.markdown(md_text)
            soup = BeautifulSoup(html, "html.parser")
            plain_text = soup.get_text(separator="\n")

            # Prepare image handling
            image_dir = f"data/{user_id}/threads/{thread_id}/images/{name}"
            os.makedirs(image_dir, exist_ok=True)

            ocr_tasks = {}
            image_names = []

            # Regex to find Markdown image syntax: ![alt](path)
            image_pattern = re.compile(r"!\[.*?\]\((.*?)\)")
            matches = image_pattern.findall(md_text)

            page_text = plain_text
            for idx, img_path in enumerate(matches, start=1):
                if not os.path.isabs(img_path):
                    # make path relative to md file
                    img_path = os.path.join(os.path.dirname(file_path), img_path)

                if not os.path.exists(img_path):
                    continue

                ext_img = Path(img_path).suffix.lstrip(".")
                image_name = f"md_img{idx}.{ext_img}"
                dest_path = os.path.join(image_dir, image_name)

                # Copy image into project folder
                shutil.copy(img_path, dest_path)
                image_names.append(image_name)

                placeholder = f"{{PENDING_{image_name}}}"
                page_text += f"\n\n[Image: {image_name}]\n{placeholder}"

                # Run OCR asynchronously
                ocr_tasks[placeholder] = asyncio.create_task(image_parser(dest_path))

            # Wait for OCR tasks
            for placeholder, task in ocr_tasks.items():
                try:
                    image_text = await task
                except Exception as e:
                    print(f"Error parsing Markdown image: {e}")
                    image_text = "[Image OCR failed]"

                page_text = page_text.replace(placeholder, image_text, 1)

            doc_id = str(uuid.uuid4())
            await sio.emit(
                f"{user_id}/progress",
                {"message": f"Processed {file_name} (Markdown) successfully"},
            )

            return Document(
                id=doc_id,
                type="markdown",
                file_name=file_name or os.path.basename(file_path),
                content=[Page(number=1, text=page_text, images=image_names)],
                title=title,
                full_text=md_text,  # preserve original markdown
            )

        except Exception as e:
            print(f"Error processing Markdown file {file_name}: {str(e)}")
            return None

    if ext in {".xls", ".csv"}:
        try:

            # Read Excel or CSV file
            if ext == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Convert to plain text
            text = df.to_string(index=False)

            doc_id = str(uuid.uuid4())
            await sio.emit(
                f"{user_id}/progress",
                {"message": f"Processed {file_name} (Excel/CSV) successfully"},
            )

            return Document(
                id=doc_id,
                type="spreadsheet",
                file_name=file_name or os.path.basename(file_path),
                content=[Page(number=1, text=text)],
                title=title,
                full_text=text,
            )

        except Exception as e:
            print(f"Error processing Excel/CSV file {file_name}: {str(e)}")
            return None
    
    # --- Handle PowerPoint files ---
    if ext in {".ppt", ".pptx"}:
        prs = Presentation(file_path)
        pages = []
        combined_texts = []
        ocr_tasks = {}
        image_dir = f"data/{user_id}/threads/{thread_id}/images/{name}"
        os.makedirs(image_dir, exist_ok=True)

        for slide_number, slide in enumerate(prs.slides, start=1):
            # Extract text
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            page_text = "\n".join(slide_text)

            image_names = []

            # Extract images
            for shape_index, shape in enumerate(slide.shapes, start=1):
                if shape.shape_type == 13:  # PICTURE
                    image = shape.image
                    image_bytes = image.blob
                    image_ext = image.ext
                    image_name = f"slide{slide_number}_img{shape_index}.{image_ext}"
                    image_path = os.path.join(image_dir, image_name)

                    with open(image_path, "wb") as f:
                        f.write(image_bytes)

                    placeholder = f"{{PENDING_{image_name}}}"
                    page_text += f"\n\n[Image: {image_name}]\n{placeholder}"
                    image_names.append(image_name)

                    ocr_tasks[placeholder] = asyncio.create_task(
                        image_parser(image_path)
                    )

            combined_texts.append(page_text)
            pages.append(Page(number=slide_number, text=page_text, images=image_names))

        # Wait for OCR tasks
        for placeholder, task in ocr_tasks.items():
            try:
                image_text = await task
            except Exception as e:
                print(f"Error parsing PPT image: {e}")
                image_text = "[Image OCR failed]"

            for page in pages:
                if placeholder in page.text:
                    page.text = page.text.replace(placeholder, image_text, 1)
            combined_texts = [
                txt.replace(placeholder, image_text, 1) for txt in combined_texts
            ]

        doc_id = str(uuid.uuid4())
        await sio.emit(
            f"{user_id}/progress", {"message": f"Processing {title} successfully..."}
        )
        end_time = time.time()
        print(
            f"Time taken to process {title} successfully: {end_time - start_time} seconds"
        )
        return Document(
            id=doc_id,
            type=ext[1:],
            file_name=file_name or os.path.basename(file_path),
            content=pages,
            title=title,
            full_text="\n".join(combined_texts),
        )

    # --- Handle PDFs ---
    doc = fitz.open(file_path)
    pages = []
    combined_texts = []
    ocr_tasks = {}

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        page_text = page.get_text("text")

        image_names = []
        image_dir = f"data/{user_id}/threads/{thread_id}/images/{name}"
        os.makedirs(image_dir, exist_ok=True)

        # Extract embedded raster images
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

            ocr_tasks[placeholder] = asyncio.create_task(image_parser(image_path))

        # Extract vector diagrams (save as SVG)
        svg_name = f"page{page_number + 1}.svg"
        svg_path = os.path.join(image_dir, svg_name)
        try:
            svg = page.get_svg_image()
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg)

            placeholder = f"{{VECTOR_{svg_name}}}"
            page_text += f"\n\n[VectorDiagram: {svg_name}]\n{placeholder}"

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

    # Wait for OCR tasks
    for placeholder, task in ocr_tasks.items():
        try:
            image_text = await task
        except Exception as e:
            print(f"Error parsing image: {e}")
            image_text = "[Image OCR failed]"

        for page in pages:
            if placeholder in page.text:
                page.text = page.text.replace(placeholder, image_text, 1)
        combined_texts = [
            txt.replace(placeholder, image_text, 1) for txt in combined_texts
        ]

    doc_id = str(uuid.uuid4())
    await sio.emit(
        f"{user_id}/progress", {"message": f"Processing {title} successfully..."}
    )
    end_time = time.time()
    print(
        f"Time taken to process {title} successfully: {end_time - start_time} seconds"
    )
    return Document(
        id=doc_id,
        type=ext[1:],
        file_name=file_name or os.path.basename(file_path),
        content=pages,
        title=title,
        full_text="\n".join(combined_texts),
    )
