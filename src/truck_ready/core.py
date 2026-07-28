"""Core closed-loop logic: jobs + stock → availability → pre-departure checklist.

All functions are pure (no I/O, no side effects) so they are trivial to test
and reason about. Side effects (CSV load, export, UI) live outside this module.
"""

from __future__ import annotations

from collections import defaultdict

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


def build_stock_index(inventory: list[InventoryItem]) -> dict[str, InventoryItem]:
    """Index inventory by normalized SKU for O(1) lookups.

    If duplicate SKUs exist, the last entry wins. Callers should
    deduplicate inventory before calling if that matters.
    """
    return {item.sku: item for item in inventory}


def check_job_parts(
    job: Job,
    stock_index: dict[str, InventoryItem],
) -> PartsCheckResult:
    """Evaluate every required part for a single job against current stock.

    Note: this is a per-job view against the full stock snapshot.
    It does not reserve stock across jobs. Use build_pre_departure_checklist
    for the aggregated, honest truck-level picture.
    """
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

    Aggregates demand across all jobs so the tech stages once.

    Rules:
    - If available >= needed → STAGE the full quantity.
    - If 0 < available < needed → STAGE what is on the truck AND
      PICK_UP the shortfall. Both lines appear.
    - If available == 0 → PICK_UP the full need.
    - REORDER when the part is below reorder point, or when the SKU
      is completely absent from inventory (not stocked at all).
    """
    results = check_all_jobs(jobs, inventory)
    stock_index = build_stock_index(inventory)

    # Aggregate demand: sku → total needed, highest urgency, job ids, name
    demand: dict[str, dict[str, object]] = defaultdict(
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
            entry["needed"] = int(entry["needed"]) + part.quantity_needed  # type: ignore[arg-type]
            entry["name"] = part.name
            jobs_list: list[str] = entry["jobs"]  # type: ignore[assignment]
            jobs_list.append(job.job_id)
            current_urgency: Urgency = entry["urgency"]  # type: ignore[assignment]
            if _urgency_rank(part.urgency) < _urgency_rank(current_urgency):
                entry["urgency"] = part.urgency

    to_stage: list[ChecklistItem] = []
    missing: list[ChecklistItem] = []
    reorder: list[ChecklistItem] = []

    for sku, info in demand.items():
        on_hand = stock_index.get(sku)
        available = on_hand.quantity if on_hand else 0
        needed = int(info["needed"])  # type: ignore[arg-type]
        shortfall = max(0, needed - available)
        urgency: Urgency = info["urgency"]  # type: ignore[assignment]
        name = str(info["name"])
        related = sorted(set(info["jobs"]))  # type: ignore[arg-type]

        # Stage whatever is actually on the truck
        if available > 0:
            stage_qty = min(available, needed)
            to_stage.append(
                ChecklistItem(
                    sku=sku,
                    name=name,
                    quantity=stage_qty,
                    action=Action.STAGE,
                    urgency=urgency,
                    related_jobs=related,
                    notes="On truck — stage before departure",
                )
            )

        # Pick up the shortfall
        if shortfall > 0:
            missing.append(
                ChecklistItem(
                    sku=sku,
                    name=name,
                    quantity=shortfall,
                    action=Action.PICK_UP,
                    urgency=urgency,
                    related_jobs=related,
                    notes=f"Need {shortfall} more (have {available})",
                )
            )

        # Reorder when below reorder point OR SKU not stocked at all
        if on_hand is None:
            reorder.append(
                ChecklistItem(
                    sku=sku,
                    name=name,
                    quantity=max(needed, 2),
                    action=Action.REORDER,
                    urgency=urgency,
                    related_jobs=related,
                    notes="Not in inventory — add to stock list",
                )
            )
        elif on_hand.quantity <= on_hand.reorder_point:
            reorder.append(
                ChecklistItem(
                    sku=sku,
                    name=name,
                    quantity=max(
                        on_hand.reorder_point * 2,
                        shortfall or on_hand.reorder_point,
                    ),
                    action=Action.REORDER,
                    urgency=urgency,
                    related_jobs=related,
                    notes="Below reorder point + active demand",
                )
            )

    to_stage.sort(key=lambda i: _urgency_rank(i.urgency))
    missing.sort(key=lambda i: _urgency_rank(i.urgency))
    reorder.sort(key=lambda i: _urgency_rank(i.urgency))

    total_required = len(demand)
    ready_skus = 0
    for sku, info in demand.items():
        available = stock_index[sku].quantity if sku in stock_index else 0
        if int(info["needed"]) <= available:  # type: ignore[arg-type]
            ready_skus += 1

    score = (ready_skus / total_required) if total_required > 0 else 1.0

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
        RequiredPart(
            sku="CAP-45-5",
            name="Dual Run Capacitor 45/5 MFD",
            quantity_needed=1,
            urgency=Urgency.HIGH,
        ),
        RequiredPart(
            sku="CAP-35-5",
            name="Dual Run Capacitor 35/5 MFD",
            quantity_needed=1,
            urgency=Urgency.MEDIUM,
        ),
        RequiredPart(
            sku="CONT-30A",
            name="Contactor 30A 1-Pole",
            quantity_needed=1,
            urgency=Urgency.HIGH,
        ),
        RequiredPart(
            sku="FILTER-20x25",
            name="Air Filter 20x25x1 MERV 8",
            quantity_needed=2,
            urgency=Urgency.LOW,
        ),
    ]

    if (
        "install" in normalized
        or "heat_pump" in normalized
        or "replacement" in normalized
    ):
        return [
            RequiredPart(
                sku="LINESET-50",
                name="Line Set 50 ft",
                quantity_needed=1,
                urgency=Urgency.CRITICAL,
            ),
            RequiredPart(
                sku="PAD-CONC",
                name="Concrete Pad",
                quantity_needed=1,
                urgency=Urgency.HIGH,
            ),
            RequiredPart(
                sku="WHIP-6/3",
                name="Disconnect Whip 6/3",
                quantity_needed=1,
                urgency=Urgency.HIGH,
            ),
            RequiredPart(
                sku="FILTER-20x25",
                name="Air Filter 20x25x1 MERV 8",
                quantity_needed=2,
                urgency=Urgency.MEDIUM,
            ),
        ]

    if "maintenance" in normalized or "tune" in normalized:
        return [
            RequiredPart(
                sku="FILTER-20x25",
                name="Air Filter 20x25x1 MERV 8",
                quantity_needed=2,
                urgency=Urgency.MEDIUM,
            ),
            RequiredPart(
                sku="FILTER-16x25",
                name="Air Filter 16x25x1 MERV 8",
                quantity_needed=1,
                urgency=Urgency.LOW,
            ),
            RequiredPart(
                sku="CAP-45-5",
                name="Dual Run Capacitor 45/5 MFD",
                quantity_needed=1,
                urgency=Urgency.MEDIUM,
            ),
        ]

    return common_service
