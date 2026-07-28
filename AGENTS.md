# AGENTS.md — Truck Ready HVAC

Short, high-signal instructions for any coding agent working on this repository.

## What this project is

One closed loop for small HVAC contractors:

**jobs + truck stock → parts availability → pre-departure checklist → offline export**

Nothing else. No multi-agent platform, no orchestration layer, no AI copilot surface.

## Invariants (do not break)

1. **Core is pure.** `src/truck_ready/core.py` must remain free of I/O, side effects, Streamlit, CSV, network, or filesystem calls. All decision logic lives here.
2. **Models are the source of truth.** Validation and serialization happen through Pydantic models in `models.py`. Do not invent parallel dict shapes.
3. **One closed loop.** Features that expand beyond the four steps above require an explicit product decision, not opportunistic scope creep.
4. **Partial staging is correct behavior.** If stock has 1 and jobs need 3, the checklist must STAGE 1 *and* PICK_UP 2. Both lines appear.
5. **Absent SKUs must produce REORDER.** A required part that does not exist in inventory still generates a reorder suggestion.

## Tooling (exact)

- Python ≥ 3.11
- Package manager: pip (editable install)
- Lint + format: `ruff check src tests` and `ruff format --check src tests`
- Tests: `pytest -v --cov=truck_ready --cov-report=term-missing`
- Type check (when needed): `mypy src`
- UI: `streamlit run app.py`

Always run the quality gates above before considering a change complete.

## Layout

```
src/truck_ready/
  models.py      # Pydantic domain models (Urgency, Action, InventoryItem, Job, …)
  core.py        # Pure functions only
  export.py      # JSON serialization for offline use
  io.py          # CSV → domain model loaders (thin adapter)
  seed.py        # Demo data
app.py           # Streamlit thin UI
tests/           # pytest, importlib mode
data/samples/    # Example CSVs for pilots
docs/            # Longer architecture + CSV format notes
```

## How to extend safely

- New domain rules → pure function in `core.py` + tests.
- New data source (CSV, future API) → thin adapter under `io.py` or a new adapter module. Never pull I/O into core.
- UI changes stay in `app.py` (or a future thin CLI).
- Prefer stdlib + Pydantic. Do not add pandas, polars, or heavy frameworks without a documented need.

## Current next slice

CSV upload path is implemented. Next high-value items (only if a real pilot needs them):

- Printable PDF checklist
- Hosted demo link
- Explicit parts column / second parts CSV if contractors supply exact BOMs

## Do not

- Introduce multi-agent or LLM orchestration into this repo.
- Soften the pure-core boundary.
- Add dependencies that are not required for the closed loop.
