"""Tests for offline checklist export."""

from __future__ import annotations

import json
from pathlib import Path

from truck_ready.core import build_pre_departure_checklist
from truck_ready.export import (
    checklist_to_dict,
    checklist_to_json_string,
    export_checklist_json,
)
from truck_ready.seed import demo_inventory, demo_jobs


def test_checklist_to_dict_roundtrip_keys() -> None:
    checklist = build_pre_departure_checklist(
        jobs=demo_jobs(),
        inventory=demo_inventory(),
    )
    data = checklist_to_dict(checklist)

    assert "jobs_covered" in data
    assert "items_to_stage" in data
    assert "items_missing" in data
    assert "reorder_suggestions" in data
    assert "overall_readiness_score" in data
    assert isinstance(data["items_to_stage"], list)


def test_checklist_to_json_string_is_valid_json() -> None:
    checklist = build_pre_departure_checklist(
        jobs=demo_jobs(),
        inventory=demo_inventory(),
    )
    raw = checklist_to_json_string(checklist)
    parsed = json.loads(raw)

    assert parsed["overall_readiness_score"] == checklist.overall_readiness_score
    assert len(parsed["jobs_covered"]) == 4


def test_export_checklist_json_writes_file(tmp_path: Path) -> None:
    checklist = build_pre_departure_checklist(
        jobs=demo_jobs(),
        inventory=demo_inventory(),
    )
    target = tmp_path / "checklist.json"
    result_path = export_checklist_json(checklist, target)

    assert result_path == target
    assert target.exists()

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["summary"] == checklist.summary
