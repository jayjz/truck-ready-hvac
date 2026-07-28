"""Truck Ready HVAC — pre-departure parts checklist for field technicians."""

from truck_ready.core import (
    build_pre_departure_checklist,
    check_all_jobs,
    check_job_parts,
    default_parts_for_job_type,
)
from truck_ready.io import CSVLoadError, load_inventory_csv, load_jobs_csv
from truck_ready.models import (
    Action,
    ChecklistItem,
    InventoryItem,
    Job,
    PartAvailability,
    PartsCheckResult,
    PreDepartureChecklist,
    RequiredPart,
    Urgency,
)
from truck_ready.pdf import checklist_to_pdf_bytes

__all__ = [
    "Action",
    "CSVLoadError",
    "ChecklistItem",
    "InventoryItem",
    "Job",
    "PartAvailability",
    "PartsCheckResult",
    "PreDepartureChecklist",
    "RequiredPart",
    "Urgency",
    "build_pre_departure_checklist",
    "check_all_jobs",
    "check_job_parts",
    "checklist_to_pdf_bytes",
    "default_parts_for_job_type",
    "load_inventory_csv",
    "load_jobs_csv",
]

__version__ = "0.2.0"
