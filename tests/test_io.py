"""Tests for CSV → domain model loaders."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from truck_ready.io import CSVLoadError, load_inventory_csv, load_jobs_csv
from truck_ready.models import Urgency

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_load_inventory_from_sample_file() -> None:
    items = load_inventory_csv(SAMPLES / "inventory.csv")
    assert len(items) >= 4
    skus = {i.sku for i in items}
    assert "CAP-45-5" in skus
    assert "LINESET-50" in skus
    lineset = next(i for i in items if i.sku == "LINESET-50")
    assert lineset.quantity == 0


def test_load_jobs_from_sample_file() -> None:
    jobs = load_jobs_csv(SAMPLES / "jobs.csv")
    assert len(jobs) >= 2
    assert all(j.required_parts for j in jobs)


def test_inventory_missing_required_column() -> None:
    raw = StringIO("sku,name\nCAP-1,Cap\n")
    with pytest.raises(CSVLoadError, match="missing required column"):
        load_inventory_csv(raw)


def test_inventory_invalid_quantity() -> None:
    raw = StringIO("sku,name,quantity\nCAP-1,Cap,-3\n")
    with pytest.raises(CSVLoadError, match="Row 2"):
        load_inventory_csv(raw)


def test_jobs_default_parts_when_column_empty() -> None:
    raw = StringIO(
        "job_id,job_type,customer_name,scheduled_date,required_parts\n"
        "JOB-1,Emergency_Repair,Test Customer,2026-07-28,\n"
    )
    jobs = load_jobs_csv(raw)
    assert len(jobs) == 1
    assert any(p.sku.startswith("CAP-") for p in jobs[0].required_parts)


def test_jobs_explicit_required_parts() -> None:
    raw = StringIO(
        "job_id,job_type,customer_name,scheduled_date,required_parts\n"
        "JOB-9,Install,Test,2026-07-28,"
        "LINESET-50:1:critical;PAD-CONC:1:high\n"
    )
    jobs = load_jobs_csv(raw)
    assert len(jobs) == 1
    parts = {p.sku: p for p in jobs[0].required_parts}
    assert parts["LINESET-50"].urgency == Urgency.CRITICAL
    assert parts["PAD-CONC"].quantity_needed == 1


def test_jobs_bad_parts_syntax() -> None:
    raw = StringIO(
        "job_id,job_type,customer_name,scheduled_date,required_parts\n"
        "JOB-9,Install,Test,2026-07-28,NOT-A-VALID-ENTRY\n"
    )
    with pytest.raises(CSVLoadError, match="Row 2"):
        load_jobs_csv(raw)
