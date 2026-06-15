# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goal
Build a Python-based reference-data product that normalizes NSE (and BSE, in progress) corporate actions, security master history, and symbol lineage into curated tables and monthly releases.

## Stack
- Python 3.11+ (currently running 3.14), virtual environment at `.venv/`
- pandas for transforms
- pytest + ruff for tests and linting
- Dolt for versioned tabular releases (repo at `dolt/`)
- Cloudflare Pages/R2 for low-cost MVP distribution

## Commands
```bash
pip install -r requirements.txt          # install deps
pytest tests/ -q                         # run all tests
pytest tests/test_symbol_lineage.py -q  # run one test file
ruff check .                             # lint
ruff format .                            # format
python pipelines/run.py                          # full pipeline, today's date
python pipelines/run.py --date 2026-05-31        # specific date
python pipelines/run.py --tasks extract,normalize # only those stages
python pipelines/run.py --dry-run                # skip Dolt commit + R2
python pipelines/run.py --no-fetch               # skip NSE downloads
python pipelines/run.py --no-dolt-commit         # skip Dolt commit/tag
```

## Session start rule
Always read `session-handoff.md` before taking any action in a new session.

## Data flow architecture
```
NSE (live) ──► data/raw/          ──► data/staging/        ──► data/curated/       ──► dolt/
               nse_symbols_*.csv       nse_symbols_           dim_issuer.csv            Dolt tables
               bhavcopy_*.csv          consolidated.csv        dim_security_master.csv   (versioned)
               nse_actions_*.csv       bhavcopy_               fact_corp_action_event.csv
                                       consolidated.csv        fact_symbol_lineage_event.csv
                                       nse_actions_            fact_adjustment_factor.csv
                                       consolidated.csv
                                       quality_report_*.json
```

Pipeline stages (task names for `--tasks`):
`extract` → `normalize` → `lineage` → `adjust` → `validate` → `load` → `export` → `manifest` → `release-notes` → `website` → `huggingface`

## Key classes per module

### `pipelines/extract/extractor.py` — `RawDataExtractor`
- `fetch_nse_symbols()`: downloads `EQUITY_L.csv` from NSE archives (no auth needed); falls back to NSE JSON API (requires session cookie), then legacy CSV
- `fetch_bhavcopy(date)`: downloads daily EOD zip from archives.nseindia.com
- `fetch_nse_corporate_actions()`: calls NSE JSON API in 30-day chunks; falls back to Playwright headless scraper; then stale-cache fallback
- `consolidate_to_staging()`: merges all daily raw files, deduplicates, writes consolidated CSVs and a `quality_report_{date}.json`

NSE source notes: EQUITY_L.csv lists only active EQ equities (~2,365 rows). `STATUS` column is absent and synthesized to `"ACTIVE"`. Corporate actions API requires `nseindia.com` session cookies set via homepage visit.

### `pipelines/normalize/normalizer.py` — `RawToCanonicalMapper`
Maps raw staging DataFrames → canonical schema tables in `data/curated/`:
- `map_to_dim_issuer(raw_symbols)` → `dim_issuer.csv`
- `map_to_dim_security_master(raw_symbols, dim_issuer)` → `dim_security_master.csv`
- `map_to_fact_corporate_action_event(raw_actions, dim_security)` → `fact_corporate_action_event.csv`

Depends on `FieldNormalizer` (field-level pure functions in `normalizers.py`) and `QualityMetadata` (confidence scoring + `score_to_flag()` in `quality.py`). Canonical action types and field aliases are in `field_mappings.yaml`. All normalize functions must be pure (no I/O).

### `pipelines/lineage/linker.py` — `SymbolLinker`
Compares symbol snapshots across time periods:
- `link_across_periods(current, historical, period_date)`: detects LISTING / DELISTING / RENAME by comparing two DataFrames, using ISIN to distinguish renames from delistings
- `cross_reference_with_actions(events, actions)`: boosts confidence (+0.15) when a corporate action corroborates a lineage event within ±30 days

Detection logic lives in `rules.py` (`LineageRulesEngine`). Confidence thresholds and weights are in `rules.yaml`.

### `pipelines/adjustments/adjuster.py` — `AdjustmentFactorBuilder`
- `build_from_corporate_actions(actions, symbols)`: computes cumulative backward adjustment factors for SPLIT / BONUS / REVERSE_SPLIT events
- Delegates per-event calculation to `AdjustmentCalculator` in `calculator.py`
- Validates output via `_validate_factors()`: all factors > 0, total = split × bonus, no duplicate (security_id, as_of_date)

### `pipelines/publish/`
| File | Class | Purpose |
|---|---|---|
| `dolt_importer.py` | `DoltImporter` | Loads curated CSVs into Dolt, commits, tags |
| `data_validator.py` | `DataValidator` | Post-import QA checks; gates Dolt commits |
| `sample_generator.py` | `SampleGenerator` | Generates free/paid-tier sample bundles |
| `packager.py` | `Packager` | Zips bundles; uploads to R2 |
| `manifest_builder.py` | `ManifestBuilder` | Writes per-release manifest + exports log |
| `access_manager.py` | `AccessManager` | Buyer registry (flat CSV); signed R2 URLs |
| `release_notifier.py` | `ReleaseNotifier` | Generates versioned release notes files |
| `website_updater.py` | `WebsiteUpdater` | Injects release card into `website/landing-page/` |
| `huggingface_publisher.py` | `HuggingFacePublisher` | Pushes security master to HuggingFace Datasets |

`config.yaml` defines tier contents, R2 bucket, email settings. Buyer state lives in `data/buyers/` (never committed).

## Dolt schema overview
Tables in `dolt/schema.sql`:
- Dims: `dim_exchange`, `dim_issuer`, `dim_security_master`, `dim_symbol_alias`, `dim_corporate_action_type`
- Facts: `fact_equity_eod`, `fact_corporate_action_event`, `fact_adjustment_factor`, `fact_symbol_lineage_event`, `fact_listing_status_history`
- Views: `vw_security_current`, `vw_symbol_lineage_sample`, `vw_action_timeline_sample`, `vw_adjusted_price_reference_sample`

`schema.sql` is auto-generated by `dolt schema export`; never edit it manually. Schema changes go in numbered migration files (`dolt/migration/NNN_description.sql`). Two-release deprecation cycle required before dropping columns.

## Sub-module CLAUDE.md files
Each module has its own `CLAUDE.md` with detailed rules — read them before editing that module:
- `pipelines/extract/CLAUDE.md` — no normalization inside extract, no deleting raw files
- `pipelines/normalize/CLAUDE.md` — pure function rules, column naming, null handling, date/numeric type rules
- `pipelines/lineage/CLAUDE.md` — event taxonomy, confidence scoring rules, determinism requirement
- `pipelines/adjustments/CLAUDE.md` — factor chain rules, edge cases, confidence flag taxonomy
- `pipelines/publish/CLAUDE.md` — tier definitions, halt-on-import-failure rule
- `dolt/CLAUDE.md` — migration naming, two-release deprecation cycle, release tagging

## Working rules
- Prefer small, focused edits over broad repo-wide changes.
- Do not modify generated files or raw data directories.
- Ask before changing schemas across multiple modules.
- Add or update tests for non-trivial logic changes.
- Prefer pure functions for transformation logic where possible.
- Use explicit error handling and structured logging.

## Done criteria
A task is complete only if code, tests, and any affected docs are updated together.

## Open work (as of 2026-06-15)
- BSE Symbol Master & Lineage expansion — phases B1–B8 defined in `todo.md`; nothing implemented yet
- Test suite exists but has limited coverage; `session-handoff.md` has priority order for new tests
