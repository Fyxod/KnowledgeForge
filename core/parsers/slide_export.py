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

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
import asyncio
import traceback
from pdf2image import convert_from_path

from core.parsers.image import image_parser


async def export_ppt_to_pdf(ppt_path: str, output_dir: str) -> Optional[str]:
    """
    Convert PowerPoint file to PDF using LibreOffice.

    Args:
        ppt_path: Path to the PowerPoint file
        output_dir: Directory to save the PDF

    Returns:
        Path to the generated PDF, or None if conversion failed
    """
    try:
        # Check if LibreOffice is available
        result = subprocess.run(
            ["which", "libreoffice"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("[LibreOffice] Not found. Please install LibreOffice:")
            print("  sudo apt-get install libreoffice")
            return None

        # Convert PPT to PDF
        pdf_filename = Path(ppt_path).stem + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)

        print(f"[LibreOffice] Converting {ppt_path} to PDF...")

        # Use LibreOffice headless mode to convert
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", output_dir,
                ppt_path,
            ],
            capture_output=True,
            text=True,
            timeout=90  # 90 second timeout
        )

        if result.returncode != 0:
            print(f"[LibreOffice] Conversion failed: {result.stderr}")
            return None

        if os.path.exists(pdf_path):
            print(f"[LibreOffice] Successfully converted to {pdf_path}")
            return pdf_path
        else:
            print(f"[LibreOffice] PDF file not created at {pdf_path}")
            return None

    except subprocess.TimeoutExpired:
        print("[LibreOffice] Conversion timed out")
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
            dpi=300,  # High DPI for better OCR
            output_folder=output_dir,
            fmt="png",
            thread_count=4
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

        # Process images in parallel
        ocr_tasks = []
        for image_path in image_paths:
            task = asyncio.create_task(image_parser(image_path))
            ocr_tasks.append(task)

        # Wait for all OCR tasks to complete
        ocr_results = await asyncio.gather(*ocr_tasks, return_exceptions=True)

        # Process results
        results = []
        for i, result in enumerate(ocr_results, start=1):
            if isinstance(result, Exception):
                print(f"[OCR] Error processing slide {i}: {result}")
                results.append("")
            else:
                print(f"[OCR] Successfully processed slide {i}")
                results.append(result)

        return results

    except Exception as e:
        print(f"[OCR] Exception: {e}")
        return [""] * len(image_paths)


async def export_and_ocr_ppt(
    ppt_path: str,
    user_id: str,
    thread_id: str
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

        # Step 2: Convert PDF to images
        image_paths = await convert_pdf_to_images(pdf_path, temp_dir)
        if not image_paths:
            print("[Export] Failed to convert PDF to images")
            return None

        # Step 3: OCR slide images
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


async def export_and_ocr_ppt_with_fallback(
    ppt_path: str,
    user_id: str,
    thread_id: str
) -> List[str]:
    """
    Export PowerPoint slides as images and perform OCR with fallback.

    If LibreOffice is not available, returns empty list (graceful degradation).

    Args:
        ppt_path: Path to the PowerPoint file
        user_id: User ID for organizing output
        thread_id: Thread ID for organizing output

    Returns:
        List of OCR results for each slide (empty if LibreOffice not available)
    """
    try:
        results = await export_and_ocr_ppt(ppt_path, user_id, thread_id)
        if results is None:
            print("[Export] LibreOffice export failed, returning empty results")
            return []
        return results

    except Exception as e:
        print(f"[Export] Exception in export_and_ocr_ppt_with_fallback: {e}")
        return []
