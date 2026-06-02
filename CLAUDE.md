# Project: TickerTruth — India Symbol History and Corporate Actions Truth Layer

## Goal
Build a Python-based reference-data product that normalizes NSE corporate actions, security master history, and symbol lineage into curated tables and monthly releases.

## Stack
- Python 3.11+ (currently running 3.14)
- pandas for transforms
- pytest for tests
- SQL for curated output tables
- Dolt for versioned tabular releases
- Cloudflare Pages/R2 for low-cost MVP distribution

## Important folders
- `pipelines/extract/` — source ingestion (NSE equity master, bhavcopy, corporate actions)
- `pipelines/normalize/` — cleanup and canonicalization
- `pipelines/lineage/` — symbol and entity history logic
- `pipelines/adjustments/` — adjustment factor logic
- `pipelines/publish/` — Dolt import, sample generation, packaging, access, release delivery
- `pipelines/run.py` — end-to-end pipeline orchestrator (entry point)
- `tests/` — unit and regression tests
- `docs/` — methodology, release notes, product docs
- `dolt/` — versioned Dolt schema and seed data
- `website/` — Cloudflare Pages site (landing page, docs mirror)
- `.github/workflows/` — CI (ci.yml), nightly data refresh (nightly.yml), release automation (release.yml)

## Pipeline entry point
```
python pipelines/run.py                          # full run, today's date
python pipelines/run.py --date 2026-05-31        # specific date
python pipelines/run.py --tasks extract,normalize # only those stages
python pipelines/run.py --dry-run                # skip Dolt commit + R2
python pipelines/run.py --no-fetch               # skip NSE downloads
python pipelines/run.py --no-dolt-commit         # skip Dolt commit/tag
```

## Working rules
- Prefer small, focused edits over broad repo-wide changes.
- Do not modify generated files or raw data directories.
- Ask before changing schemas across multiple modules.
- Add or update tests for non-trivial logic changes.
- Prefer pure functions for transformation logic where possible.
- Use explicit error handling and structured logging.
- Always read session-handoff.md at the start of a new session before taking any action

## Commands
- Install deps: `pip install -r requirements.txt`
- Run tests: `pytest tests/ -q`
- Run one test file: `pytest tests/test_symbol_lineage.py -q`
- Run lint: `ruff check .`
- Format: `ruff format .`

## Done criteria
A task is complete only if code, tests, and any affected docs are updated together.