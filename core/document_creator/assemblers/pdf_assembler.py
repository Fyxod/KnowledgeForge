from datetime import datetime
from typing import List, Optional

from fpdf import FPDF

from core.document_creator.assemblers.base import BaseDocumentAssembler
from core.document_creator.state import DocumentCreatorConfig, SectionState


class _ReportPDF(FPDF):
    """Custom FPDF subclass with headers and footers."""

    def __init__(self, doc_title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = doc_title

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
        pdf.multi_cell(0, 14, title, align="C")
        pdf.ln(8)

        # Subtitle
        if subtitle:
            pdf.set_font("Helvetica", "", 14)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 8, subtitle, align="C")
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
        heading = section_state.spec.title
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
            pdf.multi_cell(0, 5, f"Key Takeaway: {version.key_takeaway}")
            pdf.ln(4)

        # Content
        if version.content:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 41, 59)
            for para in version.content.split("\n"):
                text = para.strip()
                if text:
                    pdf.multi_cell(0, 6, text)
                    pdf.ln(3)

        # Bullet points
        if version.bullet_points:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 41, 59)
            for bullet in version.bullet_points:
                pdf.cell(8)  # indent
                pdf.multi_cell(0, 6, f"\u2022  {bullet}")
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

        # Calculate column widths
        available_width = pdf.w - 20  # margins
        col_width = available_width / len(headers)

        # Header row
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(30, 41, 59)
        for header in headers:
            pdf.cell(col_width, 8, str(header)[:30], border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font("Helvetica", "", 10)
        for row_data in rows:
            for col_idx, cell_value in enumerate(row_data):
                if col_idx < len(headers):
                    pdf.cell(col_width, 7, str(cell_value)[:30], border=1)
            pdf.ln()

        pdf.ln(4)
