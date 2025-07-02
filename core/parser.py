import io
import os
import shutil
import fitz
import pytesseract
from pathlib import Path
from PIL import Image
from kreuzberg import ExtractionResult, extract_file
from app.socket import sio
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "../worklets")

image_dir = os.path.join(PROJECT_ROOT, "./resources/extracted_images")
archive_dir = os.path.join(PROJECT_ROOT, "./resources/archived_images")

os.makedirs(image_dir, exist_ok=True)
os.makedirs(archive_dir, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.rtf', '.txt', '.epub', '.odt','.ppt', '.pptx','.xls', '.xlsx', '.csv','.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif','.html', '.xml',
}


async def extract_document(name, sid):
    """
    Extracts text content and images from a document file, performs OCR on the images,
    and emits progress updates via a socket connection.
    Args:
        name (str): The name of the document file to be processed.
        sid (str): The session ID for emitting progress updates via socket.
    Raises:
        ValueError: If the file type is not supported.
    Returns:
        str: The extracted text content from the document, including OCR results from images.
    Workflow:
        1. Validates the file extension against supported types.
        2. Extracts the file content using an asynchronous extraction function.
        3. Moves any existing images in the image directory to an archive directory.
        4. Opens the document and iterates through its pages to extract images.
        5. Saves extracted images to the image directory.
        6. Performs OCR on the images and appends the extracted text to the result.
        7. Emits progress updates during the OCR process.
    """

    file_path = os.path.join(UPLOAD_DIR, name)
    ext = Path(name).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    
    try:
        result: ExtractionResult = await extract_file(file_path)
    except Exception as e:
        await sio.emit("progress", {"message": f"Error extracting file: Failed to load document (Corrupt file)"}, to=sid)
        await asyncio.sleep(5)  
        return ""

    if result.content is None:
        result.content = ""

    for filename in os.listdir(image_dir):
        src = os.path.join(image_dir, filename)
        dst = os.path.join(archive_dir, filename)
        if os.path.isfile(src):
            shutil.move(src, dst)

    doc = fitz.open(file_path)
    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))

            image_path = os.path.join(
                image_dir, f"page{page_number + 1}_img{img_index + 1}.{image_ext}"
            )
            image.save(image_path)

            # OCR the image
            await sio.emit("progress", {"message": "Extracting data from images..."}, to=sid)
            text = pytesseract.image_to_string(image)
            result.content += f" {text} \n"

    return result.content
