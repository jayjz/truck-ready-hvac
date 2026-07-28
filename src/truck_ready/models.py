"""Domain models for the Truck Ready HVAC closed loop.

Jobs + truck stock → parts availability → pre-departure checklist → offline export.
All public models are fully typed and validated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Urgency(str, Enum):
    """How critical a missing part is to completing the job today."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Action(str, Enum):
    """What the technician should do with this checklist line."""

    STAGE = "STAGE"
    PICK_UP = "PICK_UP"
    REORDER = "REORDER"


class InventoryItem(BaseModel):
    """A single part currently on a truck or in the shop."""

    sku: Annotated[str, Field(min_length=1, description="Unique part identifier")]
    name: Annotated[str, Field(min_length=1)]
    quantity: Annotated[int, Field(ge=0)]
    reorder_point: Annotated[int, Field(ge=0, default=5)]
    unit_cost: Annotated[float, Field(ge=0.0, default=0.0)]
    category: Annotated[str, Field(default="general")]

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()


class RequiredPart(BaseModel):
    """A part required for a specific job."""

    sku: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    quantity_needed: Annotated[int, Field(ge=1, default=1)]
    urgency: Urgency = Urgency.MEDIUM

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()


class Job(BaseModel):
    """A scheduled service or install job."""

    job_id: Annotated[str, Field(min_length=1)]
    job_type: Annotated[str, Field(min_length=1)]
    customer_name: Annotated[str, Field(min_length=1)]
    scheduled_date: str
    required_parts: list[RequiredPart] = Field(default_factory=list)
    assigned_tech: str | None = None
    notes: str = ""

    @field_validator("job_id")
    @classmethod
    def normalize_job_id(cls, value: str) -> str:
        return value.strip().upper()


class PartAvailability(BaseModel):
    """Availability status for one required part against current stock."""

    sku: str
    name: str
    quantity_needed: int
    quantity_on_hand: int
    is_available: bool
    shortfall: int = Field(ge=0, description="How many units are missing")
    urgency: Urgency

    @property
    def status_label(self) -> str:
        if self.is_available:
            return "READY"
        if self.urgency in {Urgency.CRITICAL, Urgency.HIGH}:
            return "MISSING — CRITICAL"
        return "MISSING"


class PartsCheckResult(BaseModel):
    """Result of checking all required parts for a single job."""

    job_id: str
    parts: list[PartAvailability]
    availability_score: Annotated[float, Field(ge=0.0, le=1.0)]
    missing_count: int = Field(ge=0)
    ready_count: int = Field(ge=0)

    @property
    def is_fully_ready(self) -> bool:
        return self.missing_count == 0


class ChecklistItem(BaseModel):
    """One line on the pre-departure checklist."""

    sku: str
    name: str
    quantity: Annotated[int, Field(ge=1)]
    action: Action
    urgency: Urgency
    related_jobs: list[str] = Field(default_factory=list)
    notes: str = ""


class PreDepartureChecklist(BaseModel):
    """The final artifact the technician takes into the field."""

    generated_at: datetime = Field(default_factory=_utc_now)
    tech_id: str | None = None
    jobs_covered: list[str]
    items_to_stage: list[ChecklistItem]
    items_missing: list[ChecklistItem]
    reorder_suggestions: list[ChecklistItem]
    overall_readiness_score: Annotated[float, Field(ge=0.0, le=1.0)]
    summary: str

    @property
    def total_items(self) -> int:
        return (
            len(self.items_to_stage)
            + len(self.items_missing)
            + len(self.reorder_suggestions)
        )
