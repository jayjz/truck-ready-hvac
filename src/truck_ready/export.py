"""Offline export helpers for the pre-departure checklist.

The JSON payload is deliberately self-contained so a technician can
open it on a phone with zero signal.
"""

from __future__ import annotations

import json
from pathlib import Path

from truck_ready.models import PreDepartureChecklist


def checklist_to_dict(checklist: PreDepartureChecklist) -> dict:
    """Serialize checklist to a plain dict suitable for JSON."""
    return checklist.model_dump(mode="json")


def export_checklist_json(
    checklist: PreDepartureChecklist,
    path: str | Path,
) -> Path:
    """Write the checklist to a JSON file and return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = checklist_to_dict(checklist)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def checklist_to_json_string(checklist: PreDepartureChecklist) -> str:
    """Return a pretty-printed JSON string for download or display."""
    return json.dumps(checklist_to_dict(checklist), indent=2)
