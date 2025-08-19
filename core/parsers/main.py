import uuid
import os
import shutil
from pathlib import Path
import asyncio
import fitz

from PIL import Image
import io

from app.socket_handler import sio
from kreuzberg import extract_file, ExtractionResult
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

    file_path = path
    ext = Path(path).suffix.lower()
    name, _ = os.path.splitext(file_name)

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext in IMAGE_EXTENSIONS:

        try:
            await sio.emit(f"{user_id}/progress", {"message": f"{title} is an image, extracting text..."})
            text = await image_parser(file_path)
            # text = "DUMMY TEXT FOR IMAGE"
        except Exception as e:
            print(f"Error processing image {file_name}: {str(e)}")
            await asyncio.sleep(3)
            return None

        doc_id = str(uuid.uuid4())
        await sio.emit(f"{user_id}/progress", {"message": f"processed {file_name} successfully"})
        return Document(
            id=doc_id,
            type=ext[1:],
            file_name=file_name or os.path.basename(file_path),
            content=[Page(number=1, text=text)],
            title=title,
            full_text=text
        )

    try:
        await sio.emit(f"{user_id}/progress", {"message": f"{file_name} is a document, extracting text..."})
        result: ExtractionResult = await extract_file(file_path)
    except Exception as e:
        print(f"Error extracting file {file_name}: {str(e)}")
        traceback.print_exc()
        return None

    if result.content is None:
        result.content = ""

    doc = fitz.open(file_path)

    pages = []
    combined_texts = []

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        page_text = page.get_text()

        image_names = []
        image_list = page.get_images(full=True)

        if image_list:
            print("there are images on this page")
            image_dir = f"data/{user_id}/threads/{thread_id}/images/{name}"
            os.makedirs(image_dir, exist_ok=True)
            await sio.emit(f"{user_id}/progress", {"message": f"Processing images from {title}..."})

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))

            image_name = f"page{page_number + 1}_img{img_index + 1}.{image_ext}"
            image_path = os.path.join(
                image_dir, image_name
            )
            image.save(image_path)

            image_text = await image_parser(image_path)
            page_text += f"\n\n[Image: {image_name}]\n{image_text}"  # Append image text to page text

            image_names.append(image_name)


        combined_texts.append(page_text)
        pages.append(Page(number=page_number + 1, text=page_text, images=image_names))

    doc_id = str(uuid.uuid4())

    await sio.emit(f"{user_id}/progress", {"message": f"Processing {title} successfully..."})
    return Document(
        id=doc_id,
        type=ext[1:],
        file_name=file_name or os.path.basename(file_path),
        content=pages,
        title=title,
        full_text="\n".join(combined_texts),
    )
