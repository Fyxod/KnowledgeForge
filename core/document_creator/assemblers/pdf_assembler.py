"""PDF assembler using fpdf2 with Unicode font support.

Uses DejaVuSans (TrueType) instead of built-in Helvetica so that all
Unicode characters produced by LLMs render correctly.  The font is
resolved in order:
  1. System font dir  (/usr/share/fonts/truetype/dejavu/ on Debian/Ubuntu)
  2. Local cache      (<project>/data/.fonts/)
  3. Auto-download    from GitHub (one-time, ~700 KB per file)
"""

import logging
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fpdf import FPDF

from core.document_creator.assemblers.base import BaseDocumentAssembler
from core.document_creator.state import DocumentCreatorConfig, SectionState

logger = logging.getLogger(__name__)

# Minimum table column width in mm
_MIN_COL_WIDTH = 15

# ── Font resolution ───────────────────────────────────────────────────────

_FONT_FAMILY = "dejavu"
_FONT_CACHE_DIR = os.path.join("data", ".fonts")

_FONT_FILES = {
    "": "DejaVuSans.ttf",
    "B": "DejaVuSans-Bold.ttf",
    "I": "DejaVuSans-Oblique.ttf",
    "BI": "DejaVuSans-BoldOblique.ttf",
}

_DEJAVU_GITHUB_BASE = (
    "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts"
    "/master/ttf/"
)

_SYSTEM_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "/usr/local/share/fonts",
]


def _find_font(filename: str) -> Optional[str]:
    """Find a font file on disk — system dirs first, then local cache."""
    for d in _SYSTEM_FONT_DIRS:
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return p
    cached = os.path.join(_FONT_CACHE_DIR, filename)
    if os.path.isfile(cached):
        return cached
    return None


def _ensure_font(filename: str) -> str:
    """Return path to *filename*, downloading from GitHub if needed."""
    path = _find_font(filename)
    if path:
        return path

    os.makedirs(_FONT_CACHE_DIR, exist_ok=True)
    dest = os.path.join(_FONT_CACHE_DIR, filename)
    url = _DEJAVU_GITHUB_BASE + filename
    logger.info("Downloading font %s from %s", filename, url)
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception:
        raise RuntimeError(
            f"Cannot find or download font {filename}. "
            f"Install fonts-dejavu-core (apt) or place {filename} in {_FONT_CACHE_DIR}/"
        )
    return dest


def _register_fonts(pdf: FPDF) -> None:
    """Register DejaVuSans font family (regular, bold, italic, bold-italic)."""
    for style, filename in _FONT_FILES.items():
        path = _ensure_font(filename)
        pdf.add_font(_FONT_FAMILY, style=style, fname=path)


# ── PDF subclass ──────────────────────────────────────────────────────────


class _ReportPDF(FPDF):
    """Custom FPDF subclass with headers and footers."""

    def __init__(self, doc_title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = doc_title

    def header(self):
        if self.page_no() > 1:
            self.set_font(_FONT_FAMILY, "I", 8)
            self.set_text_color(100, 116, 139)
            self.cell(0, 10, self.doc_title, align="L")
            self.ln(5)
            self.set_draw_color(226, 232, 240)
            self.line(10, 18, self.w - 10, 18)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font(_FONT_FAMILY, "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


# ── Assembler ─────────────────────────────────────────────────────────────


class PdfAssembler(BaseDocumentAssembler):
    """
    Assembles sections into a PDF document using fpdf2 + DejaVuSans.

    Creates a professional report with:
    - Title page
    - Styled headings and body text
    - Tables and bullet points
    - Headers, footers, and page numbers
    """

    async def assemble(
        self,
        title: str,
        subtitle: Optional[str],
        sections: List[SectionState],
        config: DocumentCreatorConfig,
        output_path: str,
    ) -> str:
        pdf = _ReportPDF(doc_title=title)
        _register_fonts(pdf)
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)

        # Title page
        self._add_title_page(pdf, title, subtitle, config)

        # Content pages
        for section_state in sections:
            if not section_state.versions:
                continue
            version = section_state.versions[section_state.selected_version_index]
            self._add_section(pdf, section_state, version)

        pdf.output(output_path)
        return output_path

    # ── Title page ────────────────────────────────────────────────────────

    def _add_title_page(self, pdf, title, subtitle, config):
        pdf.add_page()
        pdf.ln(60)

        pdf.set_font(_FONT_FAMILY, "B", 28)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 14, title, align="C")
        pdf.ln(8)

        if subtitle:
            pdf.set_font(_FONT_FAMILY, "", 14)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 8, subtitle, align="C")
            pdf.ln(8)

        # Divider
        pdf.set_draw_color(249, 115, 22)
        y = pdf.get_y()
        pdf.line(pdf.w / 2 - 30, y, pdf.w / 2 + 30, y)
        pdf.ln(12)

        # Metadata
        pdf.set_font(_FONT_FAMILY, "", 10)
        pdf.set_text_color(148, 163, 184)
        meta = (
            f"Type: {config.document_type.value.replace('_', ' ').title()} | "
            f"Audience: {config.audience.value.title()} | "
            f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        )
        pdf.multi_cell(0, 6, meta, align="C")

    # ── Section rendering ─────────────────────────────────────────────────

    def _add_section(self, pdf, section_state, version):
        heading = section_state.spec.title
        level = section_state.spec.heading_level

        if pdf.get_y() > pdf.h - 60:
            pdf.add_page()

        # Heading
        if level == 1:
            pdf.set_font(_FONT_FAMILY, "B", 18)
            pdf.set_text_color(30, 41, 59)
        elif level == 2:
            pdf.set_font(_FONT_FAMILY, "B", 14)
            pdf.set_text_color(51, 65, 85)
        else:
            pdf.set_font(_FONT_FAMILY, "B", 12)
            pdf.set_text_color(71, 85, 105)

        pdf.multi_cell(0, 10, heading)
        pdf.ln(2)

        # Key takeaway
        if version.key_takeaway:
            pdf.set_font(_FONT_FAMILY, "I", 9)
            pdf.set_text_color(249, 115, 22)
            pdf.multi_cell(0, 5, f"Key Takeaway: {version.key_takeaway}")
            pdf.ln(4)

        # Content paragraphs
        if version.content:
            pdf.set_font(_FONT_FAMILY, "", 11)
            pdf.set_text_color(30, 41, 59)
            for para in version.content.split("\n"):
                text = para.strip()
                if text:
                    pdf.multi_cell(0, 6, text)
                    pdf.ln(3)

        # Bullet points
        if version.bullet_points:
            pdf.set_font(_FONT_FAMILY, "", 11)
            pdf.set_text_color(30, 41, 59)
            indent = 8
            bullet_width = pdf.w - pdf.l_margin - pdf.r_margin - indent
            for bullet in version.bullet_points:
                pdf.set_x(pdf.l_margin + indent)
                pdf.multi_cell(bullet_width, 6, f"\u2022  {bullet}")
                pdf.ln(2)

        # Table
        if version.table_data:
            self._add_table(pdf, version.table_data)

        pdf.ln(6)

    # ── Table rendering ───────────────────────────────────────────────────

    def _add_table(self, pdf, table_data):
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        if not headers:
            return

        available_width = pdf.w - pdf.l_margin - pdf.r_margin
        max_cols = max(1, int(available_width / _MIN_COL_WIDTH))
        if len(headers) > max_cols:
            headers = headers[:max_cols]
            rows = [row[:max_cols] for row in rows]

        col_width = available_width / len(headers)

        # Header row
        pdf.set_font(_FONT_FAMILY, "B", 10)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(30, 41, 59)
        for header in headers:
            pdf.cell(col_width, 8, str(header)[:30], border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font(_FONT_FAMILY, "", 10)
        for row_data in rows:
            for col_idx, cell_value in enumerate(row_data):
                if col_idx < len(headers):
                    pdf.cell(col_width, 7, str(cell_value)[:30], border=1)
            pdf.ln()

        pdf.ln(4)
