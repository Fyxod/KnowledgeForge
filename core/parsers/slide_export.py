"""
Slide Export Module - Full Slide OCR using LibreOffice

This module provides functionality to export entire PowerPoint slides as images
and perform OCR on them. This captures ALL content including:
- Grouped shapes
- Native drawings/diagrams
- Flowcharts
- SmartArt
- Tables
- Text
- Everything visible on the slide
"""

import asyncio
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import traceback
from typing import List, Optional

from pdf2image import convert_from_path

from core.constants import EASYOCR_WORKERS
from core.parsers.image import image_parser


def _timeout_for_file(file_path: str, base: int = 120, per_mb: int = 3) -> int:
    """Scale LibreOffice timeout with file size: base + per_mb seconds per MB (min base)."""
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return max(base, int(base + size_mb * per_mb))
    except Exception:
        return base


def get_libreoffice_command() -> Optional[str]:
    """
    Detect LibreOffice executable cross-platform.
    Returns full path if found, else None.
    """

    system = platform.system().lower()

    if system == "windows":
        possible_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return shutil.which("soffice")

    # Linux / macOS
    return shutil.which("libreoffice") or shutil.which("soffice")


async def export_ppt_to_pdf(ppt_path: str, output_dir: str) -> Optional[str]:
    """
    Convert PowerPoint file to PDF using LibreOffice (async-safe).
    """

    try:
        if not os.path.exists(ppt_path):
            print(f"[Export] File not found: {ppt_path}")
            return None

        libreoffice_cmd = get_libreoffice_command()

        if not libreoffice_cmd:
            print("[LibreOffice] Not found. Please install LibreOffice.")
            return None

        pdf_filename = Path(ppt_path).stem + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)

        timeout = _timeout_for_file(ppt_path)
        print(f"[LibreOffice] Converting {ppt_path} to PDF (timeout={timeout}s)...")

        process = await asyncio.create_subprocess_exec(
            libreoffice_cmd,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            ppt_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            print(f"[LibreOffice] Conversion timed out after {timeout}s")
            return None

        if process.returncode != 0:
            print("[LibreOffice] Conversion failed:")
            print(stderr.decode())
            return None

        # LibreOffice sometimes needs a moment to finish writing
        await asyncio.sleep(1)

        if os.path.exists(pdf_path):
            print(f"[LibreOffice] Successfully converted to {pdf_path}")
            return pdf_path

        # Fallback: search directory for any pdf
        for file in os.listdir(output_dir):
            if file.lower().endswith(".pdf"):
                return os.path.join(output_dir, file)

        print("[LibreOffice] PDF not found after conversion")
        return None

    except Exception as e:
        print(f"[LibreOffice] Exception: {e}")
        return None


async def convert_pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
    """
    Convert PDF pages to images using pdf2image.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the images

    Returns:
        List of paths to the generated images
    """
    try:
        print(f"[pdf2image] Converting {pdf_path} to images...")

        # Convert PDF to images
        images = convert_from_path(
            pdf_path,
            dpi=200,  # 200 DPI sufficient for presentation text (18pt+), 56% fewer pixels than 300 DPI
            output_folder=output_dir,
            fmt="png",
            thread_count=4,
        )

        # Save images
        image_paths = []
        for i, image in enumerate(images, start=1):
            image_path = os.path.join(output_dir, f"slide_{i}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)
            print(f"[pdf2image] Saved slide {i} to {image_path}")

        print(f"[pdf2image] Successfully converted {len(images)} slides to images")
        return image_paths

    except Exception as e:
        print(f"[pdf2image] Exception: {e}")
        return []


async def ocr_slide_images(image_paths: List[str]) -> List[str]:
    """
    Perform OCR on slide images.

    Args:
        image_paths: List of paths to slide images

    Returns:
        List of OCR results for each slide
    """
    try:
        print(f"[OCR] Processing {len(image_paths)} slide images...")

        results = []
        effective_workers = min(EASYOCR_WORKERS, 3) if len(image_paths) > 30 else EASYOCR_WORKERS
        semaphore = asyncio.Semaphore(effective_workers)  # Cap for large decks

        async def process_image(image_path: str, index: int) -> str:
            async with semaphore:
                try:
                    result = await image_parser(image_path)
                    print(f"[OCR] Successfully processed slide {index + 1}")
                    return result
                except Exception as e:
                    print(f"[OCR] Error processing slide {index + 1}: {e}")
                    return ""

        # Create tasks for all images
        ocr_tasks = [process_image(path, i) for i, path in enumerate(image_paths)]

        # Wait for all OCR tasks to complete
        results = await asyncio.gather(*ocr_tasks)

        return results

    except Exception as e:
        print(f"[OCR] Exception: {e}")
        return [""] * len(image_paths)


async def pipeline_render_and_ocr(pdf_path: str, output_dir: str) -> List[str]:
    """
    CPU↔GPU Pipeline: Overlap PDF page rendering (CPU) with OCR (GPU).

    Instead of rendering ALL pages first then OCR-ing ALL pages (sequential),
    this uses an asyncio.Queue to pipeline the two stages:
      [CPU: Render slide N] → Queue → [GPU: OCR slide N]
      [CPU: Render slide N+1]       → [GPU: OCR slide N result ready]

    Expected speedup: ~30-60% for multi-slide presentations.

    Falls back to the sequential approach if pipelining fails.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save intermediate images

    Returns:
        List of OCR results for each slide
    """
    import time as _time

    try:
        print(f"[Pipeline] Starting pipelined render+OCR for {pdf_path}...")
        start = _time.time()

        # Get total page count without rendering all at once
        from pdf2image.pdf2image import pdfinfo_from_path

        try:
            info = pdfinfo_from_path(pdf_path)
            total_pages = info.get("Pages", 0)
        except Exception:
            # Fallback: render all at once and count
            total_pages = 0

        if total_pages == 0:
            # Can't determine page count, fall back to sequential
            print("[Pipeline] Cannot determine page count, falling back to sequential")
            image_paths = await convert_pdf_to_images(pdf_path, output_dir)
            return await ocr_slide_images(image_paths)

        print(f"[Pipeline] {total_pages} pages to process")

        queue = asyncio.Queue(maxsize=3)  # Buffer up to 3 rendered images
        results = [""] * total_pages
        # Cap GPU OCR concurrency for large decks to avoid VRAM exhaustion
        effective_workers = min(EASYOCR_WORKERS, 3) if total_pages > 30 else EASYOCR_WORKERS
        ocr_semaphore = asyncio.Semaphore(effective_workers)
        print(f"[Pipeline] OCR concurrency: {effective_workers} (slides={total_pages})")

        async def producer():
            """CPU-bound: render pages one at a time and enqueue."""
            for page_num in range(1, total_pages + 1):
                try:
                    # Render single page (runs in thread to avoid blocking)
                    images = await asyncio.to_thread(
                        convert_from_path,
                        pdf_path,
                        dpi=200,
                        first_page=page_num,
                        last_page=page_num,
                        fmt="png",
                        thread_count=2,
                    )
                    if images:
                        image_path = os.path.join(output_dir, f"slide_{page_num}.png")
                        await asyncio.to_thread(images[0].save, image_path, "PNG")
                        await queue.put((page_num, image_path))
                        print(f"[Pipeline] Rendered slide {page_num}/{total_pages}")
                    else:
                        await queue.put((page_num, None))
                except Exception as e:
                    print(f"[Pipeline] Render error on slide {page_num}: {e}")
                    await queue.put((page_num, None))
            # Signal completion
            await queue.put(None)

        async def consumer():
            """GPU-bound: dequeue rendered images and run OCR."""
            while True:
                item = await queue.get()
                if item is None:
                    break
                page_num, image_path = item
                if image_path is None:
                    continue
                async with ocr_semaphore:
                    try:
                        result = await image_parser(image_path)
                        results[page_num - 1] = result or ""
                        print(f"[Pipeline] OCR complete for slide {page_num}")
                    except Exception as e:
                        print(f"[Pipeline] OCR error on slide {page_num}: {e}")

        # Run producer and consumer concurrently
        await asyncio.gather(producer(), consumer())

        elapsed = _time.time() - start
        print(
            f"[Pipeline] Pipelined render+OCR complete: {total_pages} slides in {elapsed:.2f}s"
        )
        return results

    except Exception as e:
        print(f"[Pipeline] Pipeline failed, falling back to sequential: {e}")
        traceback.print_exc()
        image_paths = await convert_pdf_to_images(pdf_path, output_dir)
        return await ocr_slide_images(image_paths)


async def export_and_ocr_ppt(
    ppt_path: str, user_id: str, thread_id: str
) -> Optional[List[str]]:
    """
    Export PowerPoint slides as images and perform OCR.

    This is the main function that orchestrates the entire process:
    1. Convert PPT to PDF using LibreOffice
    2. Convert PDF to images using pdf2image
    3. OCR each slide image

    Args:
        ppt_path: Path to the PowerPoint file
        user_id: User ID for organizing output
        thread_id: Thread ID for organizing output

    Returns:
        List of OCR results for each slide, or None if process failed
    """

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix=f"ppt_export_{user_id}_{thread_id}_")

    try:
        # Step 1: Convert PPT to PDF
        pdf_path = await export_ppt_to_pdf(ppt_path, temp_dir)
        if not pdf_path:
            print("[Export] Failed to convert PPT to PDF")
            return None

        # Step 2+3: Pipeline CPU rendering with GPU OCR (overlaps the two stages)
        ocr_results = await pipeline_render_and_ocr(pdf_path, temp_dir)
        if not ocr_results:
            print(
                "[Export] Pipeline render+OCR returned no results, trying sequential fallback"
            )
            image_paths = await convert_pdf_to_images(pdf_path, temp_dir)
            if not image_paths:
                print("[Export] Failed to convert PDF to images")
                return None
            ocr_results = await ocr_slide_images(image_paths)

        return ocr_results

    except Exception as e:
        print(f"[Export] Exception: {e}")
        traceback.print_exc()
        return None

    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
            print(f"[Export] Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"[Export] Failed to clean up temporary directory: {e}")


async def ocr_from_pdf(pdf_path: str) -> List[str]:
    """
    Run pipelined render+OCR on an existing PDF (no LibreOffice conversion).

    Use this when the caller already holds a shared PDF to avoid redundant conversions.
    """
    temp_dir = tempfile.mkdtemp(prefix="ppt_ocr_")
    try:
        results = await pipeline_render_and_ocr(pdf_path, temp_dir)
        if not results:
            image_paths = await convert_pdf_to_images(pdf_path, temp_dir)
            if image_paths:
                results = await ocr_slide_images(image_paths)
        return results or []
    except Exception as e:
        print(f"[Export] ocr_from_pdf failed: {e}")
        traceback.print_exc()
        return []
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


async def export_and_ocr_ppt_with_fallback(
    ppt_path: str, user_id: str, thread_id: str, pdf_path: Optional[str] = None
) -> List[str]:
    """
    Export PowerPoint slides as images and perform OCR with fallback.

    If pdf_path is provided, skips LibreOffice conversion and uses the given PDF.
    If LibreOffice is not available, returns empty list (graceful degradation).

    Args:
        ppt_path: Path to the PowerPoint file
        user_id: User ID for organizing output
        thread_id: Thread ID for organizing output
        pdf_path: Optional pre-converted PDF path to skip redundant conversion

    Returns:
        List of OCR results for each slide (empty if LibreOffice not available)
    """
    try:
        if pdf_path and os.path.exists(pdf_path):
            print(f"[Export] Reusing pre-converted PDF: {pdf_path}")
            return await ocr_from_pdf(pdf_path)

        results = await export_and_ocr_ppt(ppt_path, user_id, thread_id)
        if results is None:
            print("[Export] LibreOffice export failed, returning empty results")
            return []
        return results

    except Exception as e:
        print(f"[Export] Exception in export_and_ocr_ppt_with_fallback: {e}")
        return []


async def convert_ppt_to_pptx(ppt_path: str) -> Optional[str]:
    """
    Convert .ppt to .pptx using LibreOffice.
    Returns new .pptx path or None if failed.
    """

    try:
        if not ppt_path.lower().endswith(".ppt"):
            return ppt_path  # Already pptx

        libreoffice_cmd = get_libreoffice_command()
        if not libreoffice_cmd:
            print("[LibreOffice] Not found for PPT→PPTX conversion.")
            return None

        output_dir = os.path.dirname(ppt_path)
        timeout = _timeout_for_file(ppt_path)

        process = await asyncio.create_subprocess_exec(
            libreoffice_cmd,
            "--headless",
            "--convert-to",
            "pptx",
            "--outdir",
            output_dir,
            ppt_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            print(f"[LibreOffice] PPT→PPTX conversion timed out after {timeout}s.")
            return None

        if process.returncode != 0:
            print("[LibreOffice] PPT→PPTX conversion failed:")
            print(stderr.decode())
            return None

        converted_path = os.path.splitext(ppt_path)[0] + ".pptx"

        if os.path.exists(converted_path):
            print(f"[LibreOffice] Converted to {converted_path}")
            return converted_path

        # Fallback: search directory
        for f in os.listdir(output_dir):
            if f.lower().endswith(".pptx"):
                return os.path.join(output_dir, f)

        return None

    except Exception as e:
        print(f"[LibreOffice] Exception during PPT→PPTX: {e}")
        traceback.print_exc()
        return None
