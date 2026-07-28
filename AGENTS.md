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

## Pydantic validation strategy

We use a deliberate, lightweight set of Pydantic v2 patterns. Prefer these over custom validation code.

### Preferred patterns

- **`Annotated[T, Field(...)]`** for constraints and defaults (`min_length`, `ge=0`, `default=...`). Keeps the type and the rule together.
- **`@field_validator`** only for normalization that must happen on every construction (SKU / job_id uppercasing + strip). Do not put business rules here.
- **`StrEnum`** for closed value sets (`Urgency`, `Action`). Never free-form strings for these concepts.
- **`model_validate(dict)`** at the boundary (CSV rows → models). Never `**kwargs` construction in adapters when the input is untrusted.
- **Catch `ValidationError` once** in the adapter (`io.py`) and re-raise as `CSVLoadError` with 1-based row number + first error location/message. Contractors see human text, not Pydantic internals.

### What we deliberately avoid

- Model-level `@model_validator` unless a multi-field invariant is truly required.
- Custom root models or heavily nested validators.
- Silent coercion of bad data (e.g. turning negative quantity into 0). Fail loud with row context.
- Parallel plain-dict schemas. The Pydantic model *is* the schema.

### Testing expectation

- Unit-test model constraints and normalizers in `tests/test_models.py`.
- Unit-test adapter error paths (missing columns, bad types, bad parts syntax) in `tests/test_io.py`.
- Happy-path samples live in `data/samples/` and are loaded by the same tests.

## CSV schema versioning

Current state: **implicit schema v1**. No version column or header comment is required today. Column names are the contract (case-insensitive, extra columns ignored).

### Evolution rules

1. **Additive only for pilots.** New optional columns may be added without a version bump. Required columns are frozen until a deliberate v2.
2. **When a breaking change is needed** (rename, type change, removal of a required column):
   - Introduce an explicit `schema_version` column (or a first-line comment `# schema_version=2`).
   - Keep the old loader path for v1 for at least one pilot cycle.
   - Document the change in `docs/CSV_FORMAT.md` with a clear migration note.
3. **Do not** invent a full schema registry or migration framework. This is a spreadsheet product for small shops.
4. **Default parts fallback** (when `required_parts` is blank) is part of the v1 contract and must remain.

See `docs/CSV_FORMAT.md` for the exact column contracts.

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
- Optional `schema_version` column once a second pilot forces a breaking change

## Do not

- Introduce multi-agent or LLM orchestration into this repo.
- Soften the pure-core boundary.
- Add dependencies that are not required for the closed loop.
- Soften validation (negative quantities, empty SKUs, unknown urgencies must fail).
