"""Tests for CSV → domain model loaders."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from truck_ready.io import CSVLoadError, load_inventory_csv, load_jobs_csv
from truck_ready.models import Urgency

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_load_inventory_from_sample_file() -> None:
    items, warnings = load_inventory_csv(SAMPLES / "inventory.csv")
    assert len(items) >= 4
    skus = {i.sku for i in items}
    assert "CAP-45-5" in skus
    assert "LINESET-50" in skus
    lineset = next(i for i in items if i.sku == "LINESET-50")
    assert lineset.quantity == 0


def test_load_jobs_from_sample_file() -> None:
    jobs, warnings = load_jobs_csv(SAMPLES / "jobs.csv")
    assert len(jobs) >= 2
    assert all(j.required_parts for j in jobs)


def test_inventory_missing_required_column() -> None:
    raw = StringIO("sku,name\nCAP-1,Cap\n")
    # Missing required columns is a structural failure, so it still crashes
    with pytest.raises(CSVLoadError, match="missing required column"):
        load_inventory_csv(raw)


def test_inventory_invalid_quantity() -> None:
    raw = StringIO("sku,name,quantity\nCAP-1,Cap,-3\n")
    # Defensive parsing catches the negative quantity, skips the row, and returns a warning
    items, warnings = load_inventory_csv(raw)
    assert len(items) == 0
    assert len(warnings) == 1
    assert "Invalid inventory data" in warnings[0]


def test_jobs_default_parts_when_column_empty() -> None:
    raw = StringIO(
        "job_id,job_type,customer_name,scheduled_date,required_parts\n"
        "JOB-1,Emergency_Repair,Test Customer,2026-07-28,\n"
    )
    jobs, warnings = load_jobs_csv(raw)
    assert len(jobs) == 1
    assert any(p.sku.startswith("CAP-") for p in jobs[0].required_parts)


def test_jobs_explicit_required_parts() -> None:
    raw = StringIO(
        "job_id,job_type,customer_name,scheduled_date,required_parts\n"
        "JOB-9,Install,Test,2026-07-28,"
        "LINESET-50:1:critical;PAD-CONC:1:high\n"
    )
    jobs, warnings = load_jobs_csv(raw)
    assert len(jobs) == 1
    parts = {p.sku: p for p in jobs[0].required_parts}
    assert parts["LINESET-50"].urgency == Urgency.CRITICAL
    assert parts["PAD-CONC"].quantity_needed == 1


def test_jobs_bad_parts_syntax() -> None:
    raw = StringIO(
        "job_id,job_type,customer_name,scheduled_date,required_parts\n"
        "JOB-9,Install,Test,2026-07-28,NOT-A-VALID-ENTRY\n"
    )
    # Defensive parsing catches the bad syntax, skips the row, and returns a warning
    jobs, warnings = load_jobs_csv(raw)
    assert len(jobs) == 0
    assert len(warnings) == 1
    assert "Row 2 skipped" in warnings[0]
