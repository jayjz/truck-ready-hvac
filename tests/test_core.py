"""Tests for the pure parts availability + checklist engine."""

from __future__ import annotations

from truck_ready.core import (
    build_pre_departure_checklist,
    build_stock_index,
    check_all_jobs,
    check_job_parts,
    default_parts_for_job_type,
)
from truck_ready.models import InventoryItem, Job, RequiredPart, Urgency
from truck_ready.seed import demo_inventory, demo_jobs


def test_build_stock_index() -> None:
    inv = [
        InventoryItem(sku="CAP-45-5", name="Cap", quantity=3),
        InventoryItem(sku="CONT-30A", name="Contactor", quantity=2),
    ]
    index = build_stock_index(inv)
    assert "CAP-45-5" in index
    assert index["CONT-30A"].quantity == 2


def test_check_job_parts_all_available() -> None:
    job = Job(
        job_id="JOB-1",
        job_type="Repair",
        customer_name="Test",
        scheduled_date="2026-07-28",
        required_parts=[
            RequiredPart(sku="CAP-45-5", name="Cap", quantity_needed=1),
        ],
    )
    inv = [InventoryItem(sku="CAP-45-5", name="Cap", quantity=5)]
    result = check_job_parts(job, build_stock_index(inv))

    assert result.is_fully_ready is True
    assert result.missing_count == 0
    assert result.availability_score == 1.0
    assert result.parts[0].is_available is True


def test_check_job_parts_missing() -> None:
    job = Job(
        job_id="JOB-2",
        job_type="Install",
        customer_name="Test",
        scheduled_date="2026-07-28",
        required_parts=[
            RequiredPart(
                sku="LINESET-50",
                name="Line Set",
                quantity_needed=1,
                urgency=Urgency.CRITICAL,
            ),
        ],
    )
    inv = [InventoryItem(sku="CAP-45-5", name="Cap", quantity=5)]
    result = check_job_parts(job, build_stock_index(inv))

    assert result.is_fully_ready is False
    assert result.missing_count == 1
    assert result.availability_score == 0.0
    assert result.parts[0].shortfall == 1
    assert result.parts[0].status_label == "MISSING — CRITICAL"


def test_check_all_jobs_with_seed_data() -> None:
    results = check_all_jobs(demo_jobs(), demo_inventory())
    assert len(results) == 4
    assert all(isinstance(r.availability_score, float) for r in results)


def test_build_checklist_produces_actionable_output() -> None:
    checklist = build_pre_departure_checklist(
        jobs=demo_jobs(),
        inventory=demo_inventory(),
        tech_id="TCH-01",
    )

    assert checklist.tech_id == "TCH-01"
    assert len(checklist.jobs_covered) == 4
    assert 0.0 <= checklist.overall_readiness_score <= 1.0
    assert checklist.summary

    # LINESET-50 is in seed inventory with quantity 0 → must appear in missing
    missing_skus = {item.sku for item in checklist.items_missing}
    assert "LINESET-50" in missing_skus

    # Capacitors and filters should be stageable
    stage_skus = {item.sku for item in checklist.items_to_stage}
    assert "CAP-45-5" in stage_skus or "FILTER-20x25" in stage_skus


def test_default_parts_for_common_types() -> None:
    repair = default_parts_for_job_type("Emergency_Repair")
    install = default_parts_for_job_type("Heat_Pump_Install")
    maint = default_parts_for_job_type("HVAC_Maintenance")

    assert len(repair) >= 3
    assert any(p.sku.startswith("CAP-") for p in repair)
    assert any(p.sku == "LINESET-50" for p in install)
    assert any("FILTER" in p.sku for p in maint)
