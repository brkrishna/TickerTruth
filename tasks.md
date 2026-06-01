# India Symbol Truth Layer — Implementation Tasks

## Purpose

This document tracks progress across phases, checkpoints, and deliverables for the MVP build.

## Phase 1 — Setup and foundation

1. Project scaffolding
   - create repo structure
   - add `README.md`, `.gitignore`, and docs placeholders
   - define Python dependency management and environment
        - create .venv with python3 -m venv .venv
        - add requirements.txt or pyproject.toml
        - add pip install instructions for the venv   
2. Schema design
   - define table schemas for dimensions and facts
   - create Dolt schema files, seed data, and migrations
3. Source inventory
   - document NSE and corporate action sources
   - specify extraction targets and expected formats
4. Website/docs scaffold
   - establish Cloudflare Pages site structure
   - add product overview, methodology, pricing, and sample query docs

## Phase 2 — Data ingestion and normalization

5. Raw extraction pipeline
   - implement raw data fetch from NSE and action sources
   - persist raw files to `data/raw/`
   - consolidate data into staging files
6. Normalization pipeline
   - build data cleaning and canonicalization
   - map raw fields into the core schema
   - add provenance and quality metadata
7. Lineage pipeline
   - create ticker/name history rules
   - identify renames, splits, mergers, and delistings
   - output `fact_symbol_lineage_event`
8. Adjustment factor pipeline
   - compute corporate action adjustment factors
   - cross-check with symbol history for backtest readiness
   - output `fact_adjustment_factor`

## Phase 3 — Versioning, QA, and publishing

9. Dolt integration
   - initialize Dolt repo and import schema
   - implement Dolt load and commit logic
   - manage versioned repository change history
10. QA and validation
   - implement core data quality checks
   - create unit and integration tests in `tests/`
   - add validation for lineage, duplicates, and date consistency
11. Export and publishing
   - generate public sample CSV/Parquet releases
   - generate paid full release bundles
   - store outputs in `releases/monthly/`
12. Documentation and release notes
   - publish release notes and changelog updates
   - add sample SQL and usage examples

## Phase 4 — Automation and maintenance

13. CI/CD automation
   - add GitHub Actions for lint, tests, and docs site build
   - schedule weekly or nightly data refresh workflows
14. Release workflow automation
   - automate artifact generation on release events
   - automate R2 uploads and manifest updates
   - auto-update changelog metadata where feasible
15. Operational runbook
   - document manual refresh and release procedures
   - add troubleshooting steps for Dolt and workflows
   - define monitoring and failure recovery checks

## Phase 5 — Delivery and customer access

16. Packaging and pricing
   - define Explorer, Starter, Professional bundle contents
   - implement packaging logic for sample and paid bundles
17. Access model
   - define private R2 link delivery and DoltHub access process
   - document manual onboarding and payment steps
18. Future readiness
   - preserve schemas and sample queries for data warehouse migration
   - keep export logic decoupled from delivery channels

## Checkpoints and commits

- `phase-1-complete` — repo scaffold, schema design, docs scaffold
- `phase-2-complete` — extraction, normalization, lineage, adjustment pipelines
- `phase-3-complete` — Dolt integration, QA, export workflow, publish assets
- `phase-4-complete` — CI/CD automation, release automation, runbook
- `phase-5-complete` — delivery packaging, customer access, future migration readiness

## Bugs

Bugs discovered from `run.log` on 2026-06-01. Fix each and commit separately.

### BUG-1 — `fact_symbol_lineage_event` column name mismatch (critical)

**Symptom:** `[load] fact_symbol_lineage_event: error` on every run.

**Error:**
```
No declared columns found in df for table 'fact_symbol_lineage_event'.
Expected: ['security_id', 'old_symbol', 'new_symbol', 'change_date', 'change_reason', 'merged_with_symbol', 'source']
Got:      ['symbol_from', 'symbol_to', 'event_date', 'event_type', 'confidence', 'reason', 'corroborating_evidence']
```

**Root cause:** The lineage pipeline (`pipelines/lineage/linker.py`) emits columns in its own
internal naming convention. The Dolt schema (`dolt/schema.sql`) and the importer
(`pipelines/publish/dolt_importer.py`) expect a different set of column names.
The two sides were never reconciled.

**Fix:** Add a column-rename mapping in `dolt_importer.py` (or in the lineage runner in
`run.py`) to translate lineage output columns to the Dolt schema before import:

| Lineage output | Dolt schema |
|---|---|
| `symbol_from` | `old_symbol` |
| `symbol_to` | `new_symbol` |
| `event_date` | `change_date` |
| `event_type` | `change_reason` |
| `confidence` | _(no direct mapping — drop or add column to schema)_ |
| `reason` | _(no direct mapping — drop or map to source)_ |
| `corroborating_evidence` | _(no direct mapping — drop or serialize)_ |
| _(missing)_ | `security_id` — must be joined from `dim_security_master` on `old_symbol` |
| _(missing)_ | `merged_with_symbol` — populate from `event_type == MERGER` rows |

**Files to change:** `pipelines/publish/dolt_importer.py`, possibly `dolt/schema.sql`.

---

### BUG-2 — pandas ChainedAssignment FutureWarnings in normalizer (medium)

**Symptom:** 8 `FutureWarning: ChainedAssignmentError` messages during `[normalize]` on every run.

**Affected lines:**
- `pipelines/normalize/normalizer.py`: lines 146, 150, 151, 157, 165, 168, 176, 183
- `pipelines/normalize/quality.py`: line 77

**Root cause:** Code uses `df["col"][indexer] = value` (chained indexing). pandas 3.0
Copy-on-Write makes this a silent no-op — assignments will stop taking effect.

**Fix:** Replace every chained assignment with `df.loc[indexer, "col"] = value`
or assign to a new DataFrame. Run `pytest` and verify no values are silently dropped.

**Files to change:** `pipelines/normalize/normalizer.py`, `pipelines/normalize/quality.py`.

---

### BUG-3 — `dim_exchange` and `dim_corporate_action_type` never populated (medium)

**Symptom:** Dolt importer logs `Skipping dim_exchange — curated file not found` and
`Skipping dim_corporate_action_type — curated file not found` on every run.

**Root cause:** These are static lookup tables that should be populated once from seed
data, but the pipeline treats them like fact tables and looks for curated CSV files
that are never generated. The normalize stage has no step that writes
`data/curated/dim_exchange.csv` or `data/curated/dim_corporate_action_type.csv`.

**Fix:** Either:
- Add a normalize step that writes these static lookup CSVs from hardcoded values
  (NSE/BSE exchange records; action type taxonomy), **or**
- Teach `dolt_importer.py` to run `dolt sql < seed_corporate_actions.sql` for these
  two tables instead of looking for curated CSV files.

**Files to change:** `pipelines/normalize/normalizer.py` or `pipelines/publish/dolt_importer.py`,
and `dolt/seed_corporate_actions.sql`.

---

### BUG-4 — Corporate actions fetch fails with no cached fallback (medium)

**Symptom:** `[extract] fetch_nse_corporate_actions failed (non-fatal)` on every run
where NSE is unreachable or blocking, leaving `fact_corporate_action_event.csv` and
`fact_adjustment_factor.csv` permanently absent. The `[validate]` step then fails
`required_files_exist`.

**Error chain:**
1. Cookie handshake → `403 Forbidden`
2. JSON API → empty response (JSON parse error)
3. Playwright → `ERR_HTTP2_PROTOCOL_ERROR`
4. No fallback → 0 corporate actions → validate FAIL

**Root cause:** The extractor has no mechanism to fall back to the most recently
successfully fetched corporate actions file when all live fetch methods fail.

**Fix:** After all fetch methods fail, check for any existing `data/raw/nse_actions_*.csv`
file and use the most recent one with a warning log. This lets the rest of the pipeline
run on stale-but-present data rather than failing the validate check entirely.

**Files to change:** `pipelines/extract/extractor.py` (add stale-cache fallback in
`fetch_nse_corporate_actions`).

---

### BUG-5 — Bhavcopy consolidation silently uses a stale file with no age warning (medium)

**Symptom:** When today's bhavcopy is unavailable (market holiday, 404), the extractor
falls through to whatever existing `bhavcopy_*.csv` file is present in `data/raw/`. In
both runs on 2026-06-01 it loaded `bhavcopy_2024-05-10.csv` — nearly two years stale —
with no staleness warning:

```
WARNING   run  [extract] fetch_bhavcopy failed (non-fatal): Bhavcopy not found for 2026-06-01 (HTTP 404)
INFO      pipelines.extract.extractor  Bhavcopy EOD: loaded 2710 rows from bhavcopy_2024-05-10.csv
INFO      pipelines.extract.extractor  Bhavcopy EOD: 1 files → 2706 rows (-4 dupes) → bhavcopy_consolidated.csv
```

**Root cause:** The bhavcopy consolidation step globs all `bhavcopy_*.csv` files without
checking the date embedded in the filename against the run date. Contrast with the
corporate-actions stale-cache fallback (BUG-4 fix) which logs an explicit warning when
using a prior file.

**Fix:** After consolidation, compare the most recent bhavcopy file's date against the
run date. If the gap exceeds a threshold (e.g. 5 calendar days), log a `WARNING` with the
file name and age so operators know the EOD data is stale. Do not treat holiday gaps as an
error, but do make the staleness visible.

**Files to change:** `pipelines/extract/extractor.py` (bhavcopy consolidation logic).

---

### BUG-6 — `release_notifier` overwrites `docs/release-notes.md` on every run (medium)

**Symptom:** Every pipeline run writes a new entry to `docs/release-notes.md`:

```
INFO      pipelines.publish.release_notifier  Changelog updated → /Users/ramarkrishna/apps/ICASHTL/docs/release-notes.md
```

Both the 19:46 and 21:27 runs on 2026-06-01 did this, producing three duplicate
`### v2026.06.01` stubs with `0 securities, 0 corporate actions, 0 lineage events` in
the file — clobbering human-authored content and violating the CLAUDE.md format rules
for release notes.

**Root cause:** `release_notifier.py` prepends a new changelog entry to
`docs/release-notes.md` on every invocation with no guard against same-date duplicates
and no respect for the required release note format.

**Fix:** Either:
- Remove the `docs/release-notes.md` write from `release_notifier.py` entirely.
  `docs/release-notes.md` is a human-curated subscriber-facing document; the pipeline
  should only write to `releases/monthly/v<date>.md`. **Or**
- Add a duplicate-date guard: before prepending, check if an entry for the current
  run date already exists in `docs/release-notes.md` and skip if so.

**Files to change:** `pipelines/publish/release_notifier.py`.

---

### BUG-7 — Dolt commits are created even when `[validate]` fails (high)

**Symptom:** In the second run (21:27), the validate step explicitly fails:

```
INFO      run  [validate] [FAIL] required_files_exist — 3/5 files present and non-empty
```

Yet the pipeline still creates a Dolt commit and tag immediately after the load step:

```
INFO      pipelines.publish.dolt_importer  Dolt commit: fjc7i87cn1uar92t491uqv7oh7veatgf  tag: v2026.06.01
```

The final summary also shows `✗ validate` alongside `✓ load`.

**Root cause:** The pipeline orchestrator in `run.py` does not gate the Dolt commit on a
passing validate result. Validate and load run as independent steps; load commits
regardless of the validate outcome.

**Fix:** In `run.py`, pass the validate result into the load step and abort the Dolt
commit (but still write curated files) if any validate check returned FAIL. Add a log
line explaining the skipped commit so operators know why no tag was created.

**Files to change:** `pipelines/run.py`, possibly `pipelines/publish/dolt_importer.py`.

---

## Progress tracking notes

- Track failures and manual effort per release
- Capture scope changes or boundary exceptions
- Note when a task moves from manual to automated
