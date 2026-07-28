"""Tests for domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from truck_ready.models import (
    InventoryItem,
    Job,
    RequiredPart,
    Urgency,
)


def test_inventory_item_normalizes_sku() -> None:
    item = InventoryItem(sku="  cap-45-5  ", name="Dual Cap", quantity=3)
    assert item.sku == "CAP-45-5"


def test_inventory_item_rejects_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        InventoryItem(sku="CAP-45-5", name="Dual Cap", quantity=-1)


def test_required_part_defaults() -> None:
    part = RequiredPart(sku="CONT-30A", name="Contactor")
    assert part.quantity_needed == 1
    assert part.urgency == Urgency.MEDIUM


def test_job_normalizes_id() -> None:
    job = Job(
        job_id=" job-1001 ",
        job_type="Repair",
        customer_name="Test Customer",
        scheduled_date="2026-07-28",
    )
    assert job.job_id == "JOB-1001"
