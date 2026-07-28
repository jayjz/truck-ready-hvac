# Architecture

## Goal

Deliver a trustworthy pre-departure parts checklist that a technician can use with zero signal.

The product is deliberately narrow:

1. Jobs + current truck / shop stock
2. Parts availability evaluation
3. Prioritized pre-departure checklist (stage / pick-up / reorder)
4. Offline JSON + printable PDF export

## Layering

```
┌─────────────────────────────────────────┐
│  app.py (Streamlit) / future CLI        │  thin presentation
├─────────────────────────────────────────┤
│  io.py  ·  export.py  ·  pdf.py  · seed │  adapters (I/O allowed)
├─────────────────────────────────────────┤
│  core.py                                │  pure domain logic
├─────────────────────────────────────────┤
│  models.py                              │  Pydantic source of truth
└─────────────────────────────────────────┘
```

- **models.py** — all public data shapes. Strict validation, SKU normalization, enums.
- **core.py** — pure functions only. No filesystem, no network, no Streamlit, no CSV. Easy to unit-test and reason about under field conditions.
- **io.py** — CSV → list[InventoryItem] / list[Job]. Validation errors are turned into clear, row-numbered messages suitable for a contractor.
- **export.py** — checklist → self-contained JSON for offline use.
- **pdf.py** — checklist → printable PDF (fpdf2). Thin adapter only.
- **app.py** — demo + pilot UI. Loads data (demo or CSV), calls core, shows results, offers JSON + PDF download.

## Key domain rules (implemented in core)

- Aggregate demand across all jobs for the day so the tech stages once.
- STAGE whatever quantity is actually on the truck (partial staging is first-class).
- PICK_UP the shortfall.
- REORDER when the SKU is below reorder point *or* is completely absent from inventory.
- Urgency is taken as the highest urgency across jobs that need the part.
- Per-job availability scores are optimistic (they do not reserve stock across jobs). The checklist readiness score is the honest aggregated view.

## Why this shape

Small HVAC shops live in spreadsheets and paper. They will not adopt a multi-agent platform. They will adopt a tool that, in under two minutes, tells the tech what to stage and what to grab before the truck leaves the lot. The architecture protects that promise by keeping the decision engine pure and the adapters thin.
