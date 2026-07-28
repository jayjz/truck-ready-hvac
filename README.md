# Truck Ready HVAC

**Pre-departure parts checklist for HVAC technicians.**

Stage the right parts before the truck leaves. Export an offline checklist that works with zero signal. Finish more jobs on the first visit.

This is intentionally a single closed loop:

1. Jobs + current truck stock
2. Parts availability check
3. Clear pre-departure checklist
4. Offline JSON / printable export

No multi-agent platform. No orchestration theater. One high-signal workflow that maps directly to fewer supply-house runs and higher first-time fix rates.

## Quick Start

```bash
git clone https://github.com/jayjz/truck-ready-hvac.git
cd truck-ready-hvac

python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate          # Windows

pip install -e ".[dev]"

# Quality checks
ruff check src tests
ruff format --check src tests
pytest -v

# Launch the demo / pilot UI
streamlit run app.py
```

## Pilot path (real contractor data)

1. Prepare two CSVs following [docs/CSV_FORMAT.md](docs/CSV_FORMAT.md).
2. Sample files live in `data/samples/`.
3. In the Streamlit UI choose **Upload CSVs** and select your inventory + jobs files.
4. Review the checklist, then download the offline JSON for the tech.

The core engine never sees the CSV layer — loaders produce domain models, then the pure checklist builder runs unchanged.

## What it does

- Takes a list of jobs and current truck inventory
- Calculates which required parts are available vs missing
- Produces a prioritized pre-departure checklist
  - Stages what is already on the truck (including partial stock)
  - Flags shortfalls to pick up
  - Suggests reorders for low stock or untracked SKUs
- Exports a self-contained offline JSON payload the tech can use in the field

## Status

**v0.1.1 — CSV pilot path**

- [x] Project scaffolding + strict tooling (ruff, mypy, pytest, src layout)
- [x] Pydantic domain models + Action enum
- [x] Pure parts availability + checklist engine
- [x] Partial staging (stage what you have + pick up the rest)
- [x] Reorder for completely missing SKUs
- [x] Realistic HVAC seed data
- [x] Offline JSON export + tests
- [x] Minimal Streamlit pilot UI
- [x] GitHub Actions CI (ruff + pytest)
- [x] CSV loaders + sample data for real contractor pilots
- [x] Agent context files (`AGENTS.md`, `docs/`)
- [ ] Printable PDF checklist
- [ ] Hosted demo link

## Development Standards

- Python ≥ 3.11
- `src/` layout
- Strict typing + mypy
- Ruff for lint + format
- Pytest with importlib mode
- No untyped public functions
- Small, focused modules
- Core remains pure (see `AGENTS.md`)

## License

MIT — see [LICENSE](LICENSE).
