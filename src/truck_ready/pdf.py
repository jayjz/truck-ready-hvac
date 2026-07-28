"""Printable PDF export for the pre-departure checklist.

Thin adapter only. Core remains pure. Uses fpdf2 (lightweight, pure-Python,
Streamlit Community Cloud friendly) so a tech can print a physical sheet
before rolling with zero cell service.
"""

from __future__ import annotations

from fpdf import FPDF

from truck_ready.models import ChecklistItem, PreDepartureChecklist


class ChecklistPDF(FPDF):
    """Minimal branded PDF with header + page numbers."""

    def header(self) -> None:
        self.set_font("Helvetica", "B", 13)
        self.cell(
            0,
            7,
            "Truck Ready HVAC  -  Pre-Departure Checklist",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_font("Helvetica", size=8)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            4,
            "Stage the right parts. Finish more jobs first visit.",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-11)
        self.set_font("Helvetica", size=7)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            6,
            f"Page {self.page_no()}/{{nb}}   |   JSON offline export also available   |   truck-ready-hvac",
            align="C",
        )


def _section_header(pdf: FPDF, title: str, rgb: tuple[int, int, int]) -> None:
    pdf.set_fill_color(*rgb)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6.5, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1.5)


def _draw_checkbox(pdf: FPDF, x: float, y: float, size: float = 3.2) -> None:
    pdf.rect(x, y, size, size)


def _item_row(pdf: FPDF, item: ChecklistItem) -> None:
    """One checklist line with empty checkbox for the tech to mark."""
    start_y = pdf.get_y()
    if start_y > 260:  # near bottom of letter page
        pdf.add_page()
        start_y = pdf.get_y()

    x = pdf.l_margin
    _draw_checkbox(pdf, x, start_y + 1.2)

    pdf.set_xy(x + 5.5, start_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(38, 5, item.sku)

    pdf.set_font("Helvetica", size=9)
    name_width = 95
    truncated = item.name[:55] + ("..." if len(item.name) > 55 else "")
    pdf.cell(name_width, 5, truncated)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(18, 5, f"Qty {item.quantity}")

    pdf.set_font("Helvetica", size=8)
    urgency = item.urgency.value.upper()
    pdf.cell(0, 5, urgency, new_x="LMARGIN", new_y="NEXT")

    # Secondary line: jobs + notes
    jobs = ", ".join(item.related_jobs) if item.related_jobs else "-"
    notes = item.notes.strip() if item.notes else ""
    extra_parts = [f"Jobs: {jobs}"]
    if notes:
        extra_parts.append(notes)
    extra = "  |  ".join(extra_parts)

    pdf.set_font("Helvetica", size=7.5)
    pdf.set_text_color(90, 90, 90)
    pdf.set_x(x + 5.5)
    pdf.multi_cell(0, 3.8, extra)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1.2)


def checklist_to_pdf_bytes(checklist: PreDepartureChecklist) -> bytes:
    """Render a PreDepartureChecklist to PDF bytes ready for download or print.

    Returns raw PDF bytes (suitable for Streamlit download_button or file write).
    """
    pdf = ChecklistPDF(orientation="P", unit="mm", format="Letter")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(12, 14, 12)
    pdf.add_page()

    # Meta block
    generated = checklist.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    tech = checklist.tech_id or "-"
    score_pct = f"{checklist.overall_readiness_score:.0%}"
    jobs = ", ".join(checklist.jobs_covered) if checklist.jobs_covered else "-"

    pdf.set_font("Helvetica", size=9)
    pdf.cell(
        0,
        5,
        f"Generated: {generated}     Tech: {tech}     Readiness: {score_pct}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(0, 5, f"Jobs covered: {jobs}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)

    # Summary
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 4.5, checklist.summary)
    pdf.ln(2.5)

    has_content = False

    if checklist.items_to_stage:
        has_content = True
        _section_header(pdf, "STAGE THESE  (already on the truck)", (34, 120, 40))
        for item in checklist.items_to_stage:
            _item_row(pdf, item)
        pdf.ln(1.5)

    if checklist.items_missing:
        has_content = True
        _section_header(pdf, "MISSING - PICK UP BEFORE DEPARTURE", (160, 30, 30))
        for item in checklist.items_missing:
            _item_row(pdf, item)
        pdf.ln(1.5)

    if checklist.reorder_suggestions:
        has_content = True
        _section_header(pdf, "REORDER SUGGESTIONS", (180, 130, 20))
        for item in checklist.reorder_suggestions:
            _item_row(pdf, item)

    if not has_content:
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 12, "No items on this checklist.", align="C")

    result = pdf.output()
    return bytes(result)
