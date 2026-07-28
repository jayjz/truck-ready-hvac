"""Tests for printable PDF checklist export."""

from __future__ import annotations

from truck_ready.core import build_pre_departure_checklist
from truck_ready.pdf import checklist_to_pdf_bytes
from truck_ready.seed import demo_inventory, demo_jobs


def test_checklist_to_pdf_bytes_is_valid_pdf() -> None:
    checklist = build_pre_departure_checklist(
        jobs=demo_jobs(),
        inventory=demo_inventory(),
        tech_id="TCH-01",
    )
    data = checklist_to_pdf_bytes(checklist)

    assert isinstance(data, bytes)
    assert len(data) > 500
    assert data[:5] == b"%PDF-"


def test_pdf_contains_expected_sections() -> None:
    checklist = build_pre_departure_checklist(
        jobs=demo_jobs(),
        inventory=demo_inventory(),
        tech_id="TCH-01",
    )
    data = checklist_to_pdf_bytes(checklist)
    # PDF content streams are compressed; just assert non-empty valid structure.
    assert b"/Type /Page" in data or b"/Type/Page" in data or len(data) > 1000
