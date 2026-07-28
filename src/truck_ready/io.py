"""Thin CSV adapters that turn contractor spreadsheets into domain models.

These functions perform I/O and validation. They never call into the
pure core engine; callers compose loaders + core themselves.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import BinaryIO, TextIO

from pydantic import ValidationError

from truck_ready.core import default_parts_for_job_type
from truck_ready.models import InventoryItem, Job, RequiredPart, Urgency

# Accept both Path and common file-like objects from Streamlit / CLI.
PathLike = str | Path
FileLike = TextIO | BinaryIO | StringIO
Source = PathLike | FileLike


class CSVLoadError(Exception):
    """Raised when a CSV cannot be turned into valid domain models.

    The message is written for a human operator (contractor or tech),
    not only for developers.
    """

    def __init__(self, message: str, *, row: int | None = None) -> None:
        self.row = row
        if row is not None:
            super().__init__(f"Row {row}: {message}")
        else:
            super().__init__(message)


def _open_text(source: Source) -> tuple[TextIO, bool]:
    """Return a text stream and whether the caller must close it."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        return path.open(encoding="utf-8-sig", newline=""), True
    if isinstance(source, BinaryIO) or (
        hasattr(source, "mode") and "b" in getattr(source, "mode", "")
    ):
        # Streamlit UploadedFile and similar binary streams.
        return TextIOWrapper(source, encoding="utf-8-sig", newline=""), False
    # Already a text stream.
    return source, False  # type: ignore[return-value]


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _require_columns(
    fieldnames: Sequence[str] | None,
    required: set[str],
    label: str,
) -> dict[str, str]:
    if not fieldnames:
        raise CSVLoadError(f"{label} CSV has no header row.")

    mapping: dict[str, str] = {}
    for raw in fieldnames:
        norm = _normalize_header(raw)
        if norm:
            mapping[norm] = raw

    missing = sorted(required - set(mapping))
    if missing:
        raise CSVLoadError(
            f"{label} CSV is missing required column(s): {', '.join(missing)}. "
            f"Found columns: {', '.join(sorted(mapping)) or '(none)'}."
        )
    return mapping


def _row_to_dict(
    row: Mapping[str, str | None],
    colmap: dict[str, str],
) -> dict[str, str]:
    """Build a clean dict keyed by normalized names."""
    out: dict[str, str] = {}
    for norm, original in colmap.items():
        raw = row.get(original)
        if raw is None:
            continue
        value = str(raw).strip()
        if value != "":
            out[norm] = value
    return out


def load_inventory_csv(source: Source) -> list[InventoryItem]:
    """Load and validate an inventory CSV into InventoryItem models.

    Required columns: sku, name, quantity.
    Optional: reorder_point, unit_cost, category.
    """
    stream, should_close = _open_text(source)
    try:
        reader = csv.DictReader(stream)
        colmap = _require_columns(
            reader.fieldnames,
            required={"sku", "name", "quantity"},
            label="Inventory",
        )

        items: list[InventoryItem] = []
        for line_no, row in enumerate(reader, start=2):  # header is row 1
            data = _row_to_dict(row, colmap)
            if not data:
                continue  # blank line
            try:
                items.append(InventoryItem.model_validate(data))
            except ValidationError as exc:
                # Surface the first error cleanly.
                err = exc.errors()[0]
                loc = ".".join(str(p) for p in err.get("loc", ()))
                msg = err.get("msg", str(exc))
                raise CSVLoadError(
                    f"Invalid inventory data ({loc}): {msg}",
                    row=line_no,
                ) from exc

        return items
    finally:
        if should_close:
            stream.close()


def _parse_required_parts(raw: str) -> list[RequiredPart]:
    """Parse the optional required_parts cell.

    Format: SKU:qty[:urgency];SKU:qty[:urgency]
    """
    parts: list[RequiredPart] = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        tokens = [t.strip() for t in chunk.split(":")]
        if len(tokens) < 2:
            raise ValueError(f"Part entry '{chunk}' must be SKU:qty or SKU:qty:urgency")
        sku, qty_str, *rest = tokens
        try:
            qty = int(qty_str)
        except ValueError as exc:
            raise ValueError(f"Quantity for '{sku}' must be an integer") from exc

        urgency = Urgency.MEDIUM
        if rest:
            try:
                urgency = Urgency(rest[0].lower())
            except ValueError as exc:
                raise ValueError(
                    f"Unknown urgency '{rest[0]}' for '{sku}'. "
                    "Use critical|high|medium|low."
                ) from exc

        parts.append(
            RequiredPart(
                sku=sku,
                name=sku,  # name is unknown in this compact form
                quantity_needed=qty,
                urgency=urgency,
            )
        )
    return parts


def load_jobs_csv(source: Source) -> list[Job]:
    """Load and validate a jobs CSV into Job models.

    Required columns: job_id, job_type, customer_name, scheduled_date.
    Optional: assigned_tech, notes, required_parts.

    When required_parts is blank, default_parts_for_job_type(job_type) is used.
    """
    stream, should_close = _open_text(source)
    try:
        reader = csv.DictReader(stream)
        colmap = _require_columns(
            reader.fieldnames,
            required={"job_id", "job_type", "customer_name", "scheduled_date"},
            label="Jobs",
        )

        jobs: list[Job] = []
        for line_no, row in enumerate(reader, start=2):
            data = _row_to_dict(row, colmap)
            if not data:
                continue

            parts_raw = data.pop("required_parts", "").strip()
            try:
                if parts_raw:
                    required = _parse_required_parts(parts_raw)
                else:
                    required = default_parts_for_job_type(data["job_type"])

                job = Job.model_validate({**data, "required_parts": required})
                jobs.append(job)
            except (ValidationError, ValueError) as exc:
                if isinstance(exc, ValidationError):
                    err = exc.errors()[0]
                    loc = ".".join(str(p) for p in err.get("loc", ()))
                    msg = err.get("msg", str(exc))
                    detail = f"Invalid job data ({loc}): {msg}"
                else:
                    detail = str(exc)
                raise CSVLoadError(detail, row=line_no) from exc

        return jobs
    finally:
        if should_close:
            stream.close()
