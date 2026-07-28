"""Core closed-loop logic: jobs + stock → availability → pre-departure checklist.

All functions are pure (no I/O, no side effects) so they are trivial to test
and reason about. Side effects (CSV load, export, UI) live outside this module.
"""

from __future__ import annotations

from collections import defaultdict

from truck_ready.models import (
    ChecklistItem,
    InventoryItem,
    Job,
    PartAvailability,
    PartsCheckResult,
    PreDepartureChecklist,
    RequiredPart,
    Urgency,
)


def build_stock_index(inventory: list[InventoryItem]) -> dict[str, InventoryItem]:
    """Index inventory by normalized SKU for O(1) lookups."""
    return {item.sku: item for item in inventory}


def check_job_parts(
    job: Job,
    stock_index: dict[str, InventoryItem],
) -> PartsCheckResult:
    """Evaluate every required part for a single job against current stock."""
    parts: list[PartAvailability] = []
    ready = 0
    missing = 0

    for req in job.required_parts:
        on_hand = stock_index.get(req.sku)
        qty_available = on_hand.quantity if on_hand else 0
        shortfall = max(0, req.quantity_needed - qty_available)
        is_available = shortfall == 0

        if is_available:
            ready += 1
        else:
            missing += 1

        parts.append(
            PartAvailability(
                sku=req.sku,
                name=req.name,
                quantity_needed=req.quantity_needed,
                quantity_on_hand=qty_available,
                is_available=is_available,
                shortfall=shortfall,
                urgency=req.urgency,
            )
        )

    total = len(parts)
    score = (ready / total) if total > 0 else 1.0

    return PartsCheckResult(
        job_id=job.job_id,
        parts=parts,
        availability_score=round(score, 2),
        missing_count=missing,
        ready_count=ready,
    )


def check_all_jobs(
    jobs: list[Job],
    inventory: list[InventoryItem],
) -> list[PartsCheckResult]:
    """Run availability checks for every job."""
    stock_index = build_stock_index(inventory)
    return [check_job_parts(job, stock_index) for job in jobs]


def _urgency_rank(urgency: Urgency) -> int:
    order = {
        Urgency.CRITICAL: 0,
        Urgency.HIGH: 1,
        Urgency.MEDIUM: 2,
        Urgency.LOW: 3,
    }
    return order[urgency]


def build_pre_departure_checklist(
    jobs: list[Job],
    inventory: list[InventoryItem],
    tech_id: str | None = None,
) -> PreDepartureChecklist:
    """Produce the single artifact a technician needs before rolling.

    Aggregates across all jobs so the tech stages once instead of
    discovering missing parts job-by-job.
    """
    results = check_all_jobs(jobs, inventory)
    stock_index = build_stock_index(inventory)

    # Aggregate demand across jobs: sku → (total needed, highest urgency, job ids, name)
    demand: dict[str, dict] = defaultdict(
        lambda: {
            "needed": 0,
            "urgency": Urgency.LOW,
            "jobs": [],
            "name": "",
        }
    )

    for job, result in zip(jobs, results, strict=True):
        for part in result.parts:
            entry = demand[part.sku]
            entry["needed"] += part.quantity_needed
            entry["name"] = part.name
            entry["jobs"].append(job.job_id)
            if _urgency_rank(part.urgency) < _urgency_rank(entry["urgency"]):
                entry["urgency"] = part.urgency

    to_stage: list[ChecklistItem] = []
    missing: list[ChecklistItem] = []
    reorder: list[ChecklistItem] = []

    for sku, info in demand.items():
        on_hand = stock_index.get(sku)
        available = on_hand.quantity if on_hand else 0
        needed = info["needed"]
        shortfall = max(0, needed - available)

        if shortfall == 0:
            to_stage.append(
                ChecklistItem(
                    sku=sku,
                    name=info["name"],
                    quantity=needed,
                    action="STAGE",
                    urgency=info["urgency"],
                    related_jobs=sorted(set(info["jobs"])),
                    notes="On truck — stage before departure",
                )
            )
        else:
            missing.append(
                ChecklistItem(
                    sku=sku,
                    name=info["name"],
                    quantity=shortfall,
                    action="PICK_UP",
                    urgency=info["urgency"],
                    related_jobs=sorted(set(info["jobs"])),
                    notes=f"Need {shortfall} more (have {available})",
                )
            )
            # Also surface as reorder suggestion when below reorder point
            if on_hand and on_hand.quantity <= on_hand.reorder_point:
                reorder.append(
                    ChecklistItem(
                        sku=sku,
                        name=info["name"],
                        quantity=max(on_hand.reorder_point * 2, shortfall),
                        action="REORDER",
                        urgency=info["urgency"],
                        related_jobs=sorted(set(info["jobs"])),
                        notes="Below reorder point + active demand",
                    )
                )

    # Sort by urgency so critical items float to the top
    to_stage.sort(key=lambda i: _urgency_rank(i.urgency))
    missing.sort(key=lambda i: _urgency_rank(i.urgency))
    reorder.sort(key=lambda i: _urgency_rank(i.urgency))

    total_required = len(demand)
    ready_count = len(to_stage)
    score = (ready_count / total_required) if total_required > 0 else 1.0

    if not missing:
        summary = (
            f"All {total_required} part types are on the truck. "
            f"Stage the list and roll."
        )
    else:
        summary = (
            f"{len(missing)} part type(s) short. "
            f"Pick up before departure or risk a return trip."
        )

    return PreDepartureChecklist(
        tech_id=tech_id,
        jobs_covered=[j.job_id for j in jobs],
        items_to_stage=to_stage,
        items_missing=missing,
        reorder_suggestions=reorder,
        overall_readiness_score=round(score, 2),
        summary=summary,
    )


def default_parts_for_job_type(job_type: str) -> list[RequiredPart]:
    """Reasonable default parts list for common HVAC job types.

    Used by seed data and as a fallback when a contractor has not yet
    specified exact parts for a job.
    """
    normalized = job_type.strip().lower()

    common_service = [
        RequiredPart(sku="CAP-45-5", name="Dual Run Capacitor 45/5 MFD", quantity_needed=1, urgency=Urgency.HIGH),
        RequiredPart(sku="CAP-35-5", name="Dual Run Capacitor 35/5 MFD", quantity_needed=1, urgency=Urgency.MEDIUM),
        RequiredPart(sku="CONT-30A", name="Contactor 30A 1-Pole", quantity_needed=1, urgency=Urgency.HIGH),
        RequiredPart(sku="FILTER-20x25", name="Air Filter 20x25x1 MERV 8", quantity_needed=2, urgency=Urgency.LOW),
    ]

    if "install" in normalized or "heat_pump" in normalized or "replacement" in normalized:
        return [
            RequiredPart(sku="LINESET-50", name="Line Set 50 ft", quantity_needed=1, urgency=Urgency.CRITICAL),
            RequiredPart(sku="PAD-CONC", name="Concrete Pad", quantity_needed=1, urgency=Urgency.HIGH),
            RequiredPart(sku="WHIP-6/3", name="Disconnect Whip 6/3", quantity_needed=1, urgency=Urgency.HIGH),
            RequiredPart(sku="FILTER-20x25", name="Air Filter 20x25x1 MERV 8", quantity_needed=2, urgency=Urgency.MEDIUM),
        ]

    if "maintenance" in normalized or "tune" in normalized:
        return [
            RequiredPart(sku="FILTER-20x25", name="Air Filter 20x25x1 MERV 8", quantity_needed=2, urgency=Urgency.MEDIUM),
            RequiredPart(sku="FILTER-16x25", name="Air Filter 16x25x1 MERV 8", quantity_needed=1, urgency=Urgency.LOW),
            RequiredPart(sku="CAP-45-5", name="Dual Run Capacitor 45/5 MFD", quantity_needed=1, urgency=Urgency.MEDIUM),
        ]

    # Default / emergency repair
    return common_service
