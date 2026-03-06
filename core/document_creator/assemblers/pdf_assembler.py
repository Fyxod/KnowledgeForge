import re
import unicodedata
from datetime import datetime
from typing import List, Optional

from fpdf import FPDF

from core.document_creator.assemblers.base import BaseDocumentAssembler
from core.document_creator.state import DocumentCreatorConfig, SectionState

# Minimum column width in mm to fit at least one character at 10pt
_MIN_COL_WIDTH = 15

# Unicode → Latin-1-safe replacements for common LLM-generated characters
_UNICODE_REPLACEMENTS = {
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2013": "-",   # en dash
    "\u2014": "--",  # em dash
    "\u2026": "...", # ellipsis
    "\u2022": "*",   # bullet (we add our own bullet prefix)
    "\u2023": ">",   # triangular bullet
    "\u2043": "-",   # hyphen bullet
    "\u00a0": " ",   # non-breaking space
    "\u200b": "",    # zero-width space
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\ufeff": "",    # byte order mark
    "\u2212": "-",   # minus sign
    "\u00b7": "*",   # middle dot
    "\u2217": "*",   # asterisk operator
    "\u2192": "->",  # right arrow
    "\u2190": "<-",  # left arrow
    "\u2264": "<=",  # less-than or equal
    "\u2265": ">=",  # greater-than or equal
    "\u2260": "!=",  # not equal
    "\u00b2": "2",   # superscript 2
    "\u00b3": "3",   # superscript 3
}

# Regex to match characters outside Windows-1252 (Latin-1 superset used by fpdf2)
_NON_LATIN1_RE = re.compile(r"[^\x00-\xff]")


def _sanitize_text(text: str) -> str:
    """Replace non-Latin-1 characters with safe ASCII equivalents.

    fpdf2 built-in fonts (Helvetica, Courier, Times) only support the
    Windows-1252 character set. Characters outside this range cause
    width-calculation errors like 'Not enough horizontal space to render
    a single character'. This function normalises common Unicode chars
    produced by LLMs to safe Latin-1 equivalents.
    """
    if not text:
        return text

    # Apply explicit replacements first
    for src, dst in _UNICODE_REPLACEMENTS.items():
        if src in text:
            text = text.replace(src, dst)

    # Normalise remaining accented characters via NFKD decomposition
    # (e.g. ñ → n, ü → u) only for chars still outside Latin-1
    def _replace_char(match: re.Match) -> str:
        ch = match.group(0)
        # Try NFKD decomposition (strips accents / decomposes ligatures)
        decomposed = unicodedata.normalize("NFKD", ch)
        ascii_chars = decomposed.encode("ascii", "ignore").decode("ascii")
        if ascii_chars:
            return ascii_chars
        return "?"

    text = _NON_LATIN1_RE.sub(_replace_char, text)
    return text


class _ReportPDF(FPDF):
    """Custom FPDF subclass with headers and footers."""

    def __init__(self, doc_title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = _sanitize_text(doc_title)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 116, 139)
            self.cell(0, 10, self.doc_title, align="L")
            self.ln(5)
            # Divider line
            self.set_draw_color(226, 232, 240)
            self.line(10, 18, self.w - 10, 18)
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class PdfAssembler(BaseDocumentAssembler):
    """
    Assembles sections into a PDF document using fpdf2.

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

    def _add_title_page(self, pdf, title, subtitle, config):
        pdf.add_page()
        pdf.ln(60)

        # Title
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 14, _sanitize_text(title), align="C")
        pdf.ln(8)

        # Subtitle
        if subtitle:
            pdf.set_font("Helvetica", "", 14)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 8, _sanitize_text(subtitle), align="C")
            pdf.ln(8)

        # Divider
        pdf.set_draw_color(249, 115, 22)
        y = pdf.get_y()
        pdf.line(pdf.w / 2 - 30, y, pdf.w / 2 + 30, y)
        pdf.ln(12)

        # Metadata
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(148, 163, 184)
        meta = (
            f"Type: {config.document_type.value.replace('_', ' ').title()} | "
            f"Audience: {config.audience.value.title()} | "
            f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        )
        pdf.multi_cell(0, 6, meta, align="C")

    def _add_section(self, pdf, section_state, version):
        heading = _sanitize_text(section_state.spec.title)
        level = section_state.spec.heading_level

        # Check if we need a new page (leave room for heading + some content)
        if pdf.get_y() > pdf.h - 60:
            pdf.add_page()

        # Heading
        if level == 1:
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(30, 41, 59)
        elif level == 2:
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(51, 65, 85)
        else:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(71, 85, 105)

        pdf.multi_cell(0, 10, heading)
        pdf.ln(2)

        # Key takeaway
        if version.key_takeaway:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(249, 115, 22)
            pdf.multi_cell(0, 5, f"Key Takeaway: {_sanitize_text(version.key_takeaway)}")
            pdf.ln(4)

        # Content
        if version.content:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 41, 59)
            for para in _sanitize_text(version.content).split("\n"):
                text = para.strip()
                if text:
                    pdf.multi_cell(0, 6, text)
                    pdf.ln(3)

        # Bullet points — use explicit width calculation instead of
        # cell(8) + multi_cell(0) which is fragile with X cursor state
        if version.bullet_points:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 41, 59)
            indent = 8
            bullet_width = pdf.w - pdf.l_margin - pdf.r_margin - indent
            for bullet in version.bullet_points:
                pdf.set_x(pdf.l_margin + indent)
                pdf.multi_cell(bullet_width, 6, f"*  {_sanitize_text(bullet)}")
                pdf.ln(2)

        # Table
        if version.table_data:
            self._add_table(pdf, version.table_data)

        pdf.ln(6)

    def _add_table(self, pdf, table_data):
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        if not headers:
            return

        # Calculate column widths, capping the number of columns to fit
        available_width = pdf.w - pdf.l_margin - pdf.r_margin
        max_cols = max(1, int(available_width / _MIN_COL_WIDTH))
        if len(headers) > max_cols:
            headers = headers[:max_cols]
            rows = [row[:max_cols] for row in rows]

        col_width = available_width / len(headers)

        # Header row
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(30, 41, 59)
        for header in headers:
            pdf.cell(col_width, 8, _sanitize_text(str(header))[:30], border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font("Helvetica", "", 10)
        for row_data in rows:
            for col_idx, cell_value in enumerate(row_data):
                if col_idx < len(headers):
                    pdf.cell(col_width, 7, _sanitize_text(str(cell_value))[:30], border=1)
            pdf.ln()

        pdf.ln(4)
