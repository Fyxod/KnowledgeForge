from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import os 

class Page(BaseModel):
    number: int
    text: str
    images: Optional[List[str]] = Field(default_factory=list)  

class Document(BaseModel):
    id: str
    type: str
    file_name: str
    content: List[Page] = Field(default_factory=list)
    title: str
    full_text: str

SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.rtf', '.txt', '.epub', '.odt','.ppt', '.pptx','.xls', '.xlsx', '.csv','.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif','.html', '.xml',
}

async def extract_document(name, sid, image_parser, doc_type="document", title="Untitled"):
    """
    Args:
        name: filename
        sid: socket session id for progress updates
        image_parser: a callable async function that takes image path and returns text
        doc_type: type of document (default "document")
        title: document title
    Returns:
        Document model instance
    """

    file_path = os.path.join(UPLOAD_DIR, name)
    ext = Path(name).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    try:
        result = await extract_file(file_path)
    except Exception as e:
        await sio.emit("progress", {"message": f"Error extracting file: Failed to load document (Corrupt file)"}, to=sid)
        await asyncio.sleep(5)
        return None

    if result.content is None:
        result.content = ""

    for filename in os.listdir(image_dir):
        src = os.path.join(image_dir, filename)
        dst = os.path.join(archive_dir, filename)
        if os.path.isfile(src):
            shutil.move(src, dst)

    doc = fitz.open(file_path)

    pages = []
    combined_texts = []

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)

        page_text = page.get_text()
        combined_texts.append(page_text)
        
        image_texts = []
        image_list = page.get_images(full=True)

        if image_list:
            await sio.emit("progress", {"message": f"Extracting data from images on page {page_number + 1}..."}, to=sid)

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

            image_text = await image_parser(image_path)
            image_texts.append(image_text)
            combined_texts.append(image_text)

        pages.append(Page(number=page_number + 1, text=page_text, images=image_texts))

    doc_id = str(uuid.uuid4())

    document = Document(
        id=doc_id,
        type=doc_type,
        file_name=name,
        content=pages,
        title=title,
        full_text="\n".join(combined_texts),
    )

    return document
