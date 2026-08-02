# TickerTruth — Pending MVP Items

Derived from `low-cost-mvp-blueprint.md`. Technical bug details are in `tasks.md`.

---

## Pipeline bugs (blocking clean releases)

- [x] **BUG-7 (HIGH)** — Gate Dolt commits on passing validate result. Fixed in commit `cf04942`.
- [x] **BUG-6 (MEDIUM)** — `release_notifier.py` overwrites `docs/release-notes.md`. Fixed in commit `89e009c`.
- [x] **BUG-5 (MEDIUM)** — Stale bhavcopy consolidation gives no warning. Fixed in commit `2133fde`.

---

## Product — missing artifacts

- [x] Create `notebooks/` directory with four sample notebooks (commit `e516cb9`):
  - `sample_lineage_walkthrough.ipynb`
  - `action_event_examples.ipynb`
  - `adjusted_vs_raw_series.ipynb`
  - `broken_vs_corrected_backtest.ipynb`
- [x] Add event-confidence scoring to corporate action events — `score_to_flag()` in `quality.py`, `confidence_flag` column emitted by normalizer (commit `e516cb9`).
- [x] Build "broken vs corrected backtest" example notebook for marketing and buyer trust (commit `e516cb9`).
- [x] Market notebooks on portal — Colab badges in all four notebooks, "See It in Action" section on homepage, worked examples on methodology page, pandas cross-links on sample-queries page (commit `f2f3325`).

---

## Commercial delivery — subscriber access

- [ ] Choose and implement subscriber delivery model (pick one to start):
  - Private DoltHub repo access for paying subscribers, or
  - R2 presigned links delivered by email, or
  - Password-protected download portal on Cloudflare Pages
- [ ] Set up payment collection — UPI / Stripe / Lemon Squeezy for invoicing and receipts.
- [ ] Write customer onboarding checklist (what subscriber gets, how to access, support contact).
- [ ] Define and document the paid tier vs free tier data split (what's in Explorer vs Starter vs Professional).

---

## Go-to-market — Phase 1 soft launch

- [ ] Finalize positioning statement and primary buyer persona (quant researcher, fintech data team, broker research).
- [ ] Publish 2 technical LinkedIn posts:
  - "Why India backtests break when ticker history is wrong"
  - "Corporate actions in India — what most teams miss"
- [ ] Direct outreach to 20–30 target buyers (heads of data, quants, fintech CTOs).
- [ ] Offer 3 design-partner slots at discounted pricing in exchange for structured feedback.

---

## Go-to-market — Phase 2 first paid pilots (weeks 4–8)

- [ ] Convert 1–3 design partners to paid.
- [ ] Run monthly releases manually and improve docs based on buyer questions.
- [ ] Refine commercial packaging based on pilot feedback.

---

## Content and promotion rhythm (ongoing)

- [ ] 2 educational posts per week on LinkedIn.
- [ ] 10 direct outreach messages per week.
- [ ] 1 product update / changelog post per month.
- [ ] 1 sample notebook or walkthrough per month.
- [ ] Publish on India capital-markets communities and finance engineering groups.

---

## Phase 3 — scale test (months 3–4)

- [ ] Expand outreach to fintech product teams, quant boutiques, broker research teams.
- [ ] Add a richer paid tier (confidence flags, full provenance, bespoke exports).
- [ ] Decide: stay lean manual delivery or prepare warehouse marketplace migration (Snowflake/Databricks) — only if 3–5 customers explicitly request it.

---

## BSE Symbol Master & Lineage — Product Expansion

> **Why now:** Same methodology already solved for NSE. BSE coverage is a natural upsell to existing customers and unlocks BSE-only listings (SME board, BSE Emerge, BSE-only large caps). Primary key difference: BSE uses numeric scrip codes (e.g. 500325) instead of ticker symbols — ISIN is the natural bridge to NSE.

### Phase B1 — Data source audit & schema design ✅ (commit `31cc0c0`)

- [x] Audit all publicly available BSE data feeds — captured as source configs in `pipelines/extract/sources.yaml` (`bse_equity_master`, `bse_bhavcopy`, `bse_corporate_actions`), with quirks documented inline (no auth for bhavcopy, STATUS present unlike NSE, DD/MM/YYYY date format).
- [x] Map BSE scrip code lifecycle — documented in `pipelines/lineage/bse_scrip_history.py` docstrings (renames, status transitions, code reassignment edge case).
- [x] Design schema extensions for BSE tables — `dolt/migration/002_bse_scrip_master.sql` adds `dim_bse_scrip_master`, `fact_bse_scrip_lineage_event`, `fact_exchange_security_map`; NSE schemas untouched.
- [x] Identify gaps — BSE numeric scrip codes vs NSE tickers, BSE missing ex-date confidence penalty, handled via `BSE_MISSING_EX_DATE` flag in `bse_normalizer.py`.

### Phase B2 — BSE extract pipeline ✅ (commit `bbb59d6`)

- [x] BSE equity master, bhavcopy, and corporate actions extraction — implemented as a single `BSERawDataExtractor` class in `pipelines/extract/bse_extractor.py` (`fetch_bse_equity_master()`, `fetch_bse_bhavcopy()`, `fetch_bse_corporate_actions()`) rather than four separate files; same effect, less duplication of session/retry plumbing.
- [ ] Standalone `bse_security_history.py` for scrip master archive diffing — not built as a separate extractor; historical diffing is instead handled downstream by `BSEScripHistoryBuilder.build_lineage_events()` comparing two snapshots (Phase B4).
- [x] Wired into `pipelines/run.py` behind `--exchange bse|both` flag (`run_extract_bse()`) — NSE-only runs (`--exchange nse`, the default) unaffected.

### Phase B3 — BSE normalize pipeline ✅ (commit `99f1723`)

- [x] BSE scrip name canonicalization — `BSERawToCanonicalMapper.map_to_dim_bse_scrip_master()` in `pipelines/normalize/bse_normalizer.py` (not a separate `bse_symbol_aliases.py`).
- [x] BSE corporate action parsing into shared schema — `map_to_fact_bse_corporate_action_event()`, with `normalize_bse_action_type()` mapping 24 BSE purpose strings to canonical action codes.
- [x] BSE-specific confidence signal — missing ex_date applies a -0.15 penalty and `BSE_MISSING_EX_DATE` flag (extends `quality.py` scoring at the call site rather than inside `score_to_flag()` itself).
- [x] `tests/test_bse_normalize.py` — 35 tests covering name canonicalization, action parsing, and confidence scoring edge cases.

### Phase B4 — BSE lineage pipeline ✅ (commit `1feba9f`)

- [x] `pipelines/lineage/bse_scrip_history.py` — `BSEScripHistoryBuilder.build_lineage_events()` reconstructs LISTING / DELISTING / RENAME / CODE_REASSIGN / STATUS_CHANGE / RELISTING events; `build_status_history()` for point-in-time snapshots.
- [x] CODE_REASSIGN edge case handled — same scrip_code, different ISIN across snapshots.
- [x] Lineage events table produced in-memory (matches `fact_bse_scrip_lineage_event` schema from migration 002); not yet a named "`bse_scrip_lineage`" curated table on disk — wiring to `data/curated/` deferred since `run.py` doesn't yet call this builder directly (only `isin_bridge.py` consumes `dim_bse_scrip_master.csv` in B7's `run_lineage_bse()`).
- [x] `tests/test_bse_lineage.py` — 17 tests covering all 6 event types, determinism, and code reassignment.

### Phase B5 — NSE–BSE cross-exchange reconciliation (ISIN bridge) ✅ (commit `18349e0`)

- [x] `pipelines/lineage/isin_bridge.py` — `ISINBridgeBuilder.build()` joins NSE and BSE security masters on ISIN.
- [x] Produces `fact_exchange_security_map`: isin, nse_symbol, nse_effective_from/to, bse_scrip_code, bse_effective_from/to, is_bse_only, is_nse_only.
- [x] BSE-only / NSE-only flags implemented.
- [x] `find_ca_date_conflicts()` flags ISINs with conflicting corporate action dates across exchanges, with HIGH/MEDIUM/LOW severity.
- [x] `tests/test_isin_bridge.py` — 18 tests covering dual-listed, BSE-only, NSE-only, and CA conflict fixtures.

### Phase B6 — BSE adjustment factors ✅ (commit `1b7429b`)

- [x] `pipelines/adjustments/bse_adjuster.py` — `BSEAdjustmentFactorBuilder.build_from_bse_actions()` adapts BSE corporate actions (scrip_id → security_id rename) through the existing shared `AdjustmentCalculator`/`AdjustmentFactorBuilder` logic, rather than modifying `factors.py` directly (that file is `adjuster.py`/`calculator.py` in this codebase).
- [x] `cross_validate_with_nse()` compares BSE vs NSE cumulative factors for dual-listed securities via the ISIN bridge, flagging discrepancies by severity.
- [x] `tests/test_bse_adjustments.py` — 22 tests mirroring the NSE adjustment test suite plus cross-validation cases.

### Phase B7 — Validation, QA & release integration ✅ (commit `d8b26c8`)

- [x] Extended `pipelines/publish/data_validator.py` (this codebase's validate module) with `check_bse_files_exist()`, `check_bse_scrip_codes_valid()`, `check_bse_adjustment_factors_valid()`, `check_isin_bridge_integrity()`, and `run_bse_checks()`.
- [x] BSE validation wired into the same gate pattern as BUG-7 (`run_validate_bse()` in `run.py`).
- [x] `pipelines/run.py` orchestrator updated with `--exchange nse|bse|both` flag and BSE task runners (`run_extract_bse`, `run_normalize_bse`, `run_lineage_bse`, `run_adjust_bse`, `run_validate_bse`) across the standard task list and `--dry-run` path.
- [ ] Monthly release packaging for BSE as a separate tarball/Dolt branch — not yet done; BSE curated CSVs land in the same `data/curated/` directory as NSE today.
- [ ] BSE coverage section in `docs/methodology.md` / `docs/data-dictionary.md` — not yet done (website methodology page updated instead, see B8).
- [x] `tests/test_bse_validator.py` — 18 tests covering all 4 BSE checks and the dispatcher.

### Phase B8 — Commercial packaging & go-to-market (partial — commit `222ca7c`)

- [ ] Define BSE add-on SKU pricing — not decided; pricing page currently folds BSE into Starter/Professional/Enterprise tiers rather than a separate add-on SKU (see below).
- [ ] Gate BSE artifacts behind a BSE-tier entitlement check in delivery scripts — not done (no entitlement enforcement exists yet for any tier).
- [x] Added BSE coverage to the website: `index.html` hero badge/description/stats bar/features list updated to "NSE + BSE", plus `pricing.html` tiers updated (Starter now includes BSE scrip master + lineage, Professional includes ISIN bridge + CA conflict report, Enterprise reworded to "Dual-exchange NSE + BSE").
- [x] Created `notebooks/bse_nse_dual_listing_reconciliation.ipynb` — 5-section walkthrough: exchange coverage breakdown, dual-listed lookup, CA date conflict detection, BSE-only hidden universe, adjustment-factor cross-validation.
- [ ] LinkedIn posts ("BSE-only listings your backtest is missing", "When NSE and BSE disagree on the record date") — not drafted.
- [ ] Offer BSE coverage as an upsell in pilot conversations — pending first pilot customers (see Commercial delivery section above, still unstarted).

---

## Nice-to-have / deferred

- [ ] `releases/changelogs/` directory (blueprint calls for it alongside `releases/monthly/`).
- [ ] API-first delivery — deferred until Phase 3 or marketplace migration.

---

## Code optimization & refactor opportunities (review 2026-07-03)

> Findings from a full read-through of `pipelines/` and `tests/`. Not yet implemented — ordered roughly by impact/effort within each bucket. No code was changed as part of this review.

### NSE/BSE duplication

- [ ] **REFACTOR-1 (HIGH impact / medium effort)** — `RawDataExtractor` (`pipelines/extract/extractor.py`) and `BSERawDataExtractor` (`pipelines/extract/bse_extractor.py`) are near-identical: `fetch_*_bhavcopy`, `fetch_*_corporate_actions`, `_extract_bhavcopy_zip`, `_date_chunks`, `_consolidate_source`, `_stale_corp_actions_fallback` all mirror each other. `_extract_bhavcopy_zip` and `_date_chunks` are byte-for-byte duplicates. Extract a shared `BaseExchangeExtractor` parametrized by exchange config (URLs, column aliases, key column).
- [ ] **REFACTOR-2 (MEDIUM-HIGH impact / medium effort)** — `RawToCanonicalMapper` (`pipelines/normalize/normalizer.py`) and `BSERawToCanonicalMapper` (`pipelines/normalize/bse_normalizer.py`) both do find-column-by-aliases → normalize → dedupe → quality-flag, differing only in NSE `SYMBOL`/`security_id` vs BSE `SCRIP_CODE`/`scrip_id`. `_find_col` is identical in both files. Consolidate into one mapper parametrized by key-column name + exchange_id. Use the adapter pattern already used well in `bse_adjuster.py` (delegates to shared `AdjustmentFactorBuilder` via column rename) as the template.
- [ ] **REFACTOR-3 (MEDIUM impact / medium effort)** — `pipelines/run.py` has 10 near-identical task-runner pairs (`run_extract`/`run_extract_bse`, `run_normalize`/`run_normalize_bse`, `run_lineage`/`run_lineage_bse`, `run_adjust`/`run_adjust_bse`, `run_validate`/`run_validate_bse`) differing only in module/file names. Replace with one parametrized `run_stage(exchange, stage)` dispatcher driven by a small config table — would shrink `run.py` by roughly a third and stop NSE/BSE task logic from silently drifting apart.
- [ ] **REFACTOR-4 (LOW-MEDIUM impact / small effort)** — `ISINBridgeBuilder._enrich_with_isin_nse` / `_enrich_with_isin_bse` (`pipelines/lineage/isin_bridge.py:244-275`) are parallel logic for attaching ISIN via bridge lookup; collapse into one helper taking the exchange-key-column name as a parameter.

### Performance — pandas usage

- [ ] **PERF-1 (HIGH impact / small-medium effort)** — `AdjustmentFactorBuilder.build_from_corporate_actions` (`pipelines/adjustments/adjuster.py:92-130`) builds a new single-row DataFrame per event just to call `AdjustmentCalculator.calculate_cumulative_adjustment` (`pipelines/adjustments/calculator.py:109`), which only needs scalar `action_code`/`old_value`. Refactor the calculator to accept scalars (or vectorize with `groupby().cumprod()` over mapped SPLIT/BONUS ratios) and collapse the two together. Runs on every `adjust`/`adjust-bse` stage — scales with total corporate-action row count.
- [ ] **PERF-2 (MEDIUM-HIGH impact / small effort)** — `quality.py::add_quality_flags` (`pipelines/normalize/quality.py:72`) uses row-wise `df.apply(self._detect_issues, axis=1)`, called from every mapper (dim_issuer, dim_security_master, fact_corporate_action_event × NSE and BSE = touches every normalized row in the whole pipeline). Vectorize with boolean masks per `_CRITICAL_COLUMNS` entry, OR-combined, instead of per-row Python calls.
- [ ] **PERF-3 (MEDIUM impact / medium effort)** — `SymbolLinker.cross_reference_with_actions` (`pipelines/lineage/linker.py:210-244`) does a nested Python loop with a boolean-mask filter of `actions` per event — O(events × actions). Replace with `merge_asof` or a pre-indexed dict of date arrays by symbol; will worsen as monthly releases accumulate corporate-action history.
- [ ] **PERF-4 (MEDIUM-HIGH impact / medium effort)** — `consolidate_to_staging()` (`pipelines/extract/extractor.py:1053-1066`, BSE mirror `bse_extractor.py:619-630`) re-reads and re-concats *all* historical raw CSVs from disk on every run rather than incrementally merging only new files — O(total historical raw files) per run, grows unboundedly as `data/raw/` accumulates daily snapshots. Consider a "last consolidated" watermark.
- [ ] **PERF-5 (LOW-MEDIUM impact / small effort)** — `SymbolLinker.link_across_periods` (`pipelines/lineage/linker.py:89-102`) and `bse_scrip_history.py:244` use `iterrows()` to build ISIN↔symbol dicts; replace with vectorized `.dropna().drop_duplicates().set_index(...)` construction (pattern already used in `isin_bridge.py`).

### I/O inefficiency

- [ ] **IO-1 (HIGH impact / medium effort)** — Every stage reads/writes `.csv` for `data/raw/`, `data/staging/`, `data/curated/` despite `pipelines/extract/CLAUDE.md` stating staging should be Parquet (doc/code mismatch — see also item below). Migrating at least `data/staging/` bhavcopy (largest, highest-volume table) to Parquet would cut file size/parse time and remove the need for scattered explicit `dtype={"SCRIP_CODE": str}` workarounds across ~6 `read_csv` call sites.
- [ ] **IO-2 (MEDIUM impact / medium effort)** — Within a single `run.py` invocation, each stage function re-reads curated CSVs from disk that a prior stage in the *same process* just wrote (e.g. `dim_security_master.csv` written in `run_normalize`, re-read in `run_lineage` and `run_adjust`). Consider passing DataFrames via an in-memory run context between stages instead of round-tripping through disk every boundary.
- [ ] **IO-3 (LOW-MEDIUM impact / small effort)** — `collect_stats()` (`pipelines/run.py:350-398`) reads 8 full curated CSVs into memory purely to compute `len(df)`. Store row counts in the manifest/quality-report at the stage that produces each file instead of re-parsing full CSVs at the end.

### Structural / architectural

- [ ] **STRUCT-1 (MEDIUM impact / medium effort)** — `pipelines/run.py` is 794 lines with 18 near-duplicated `run_*` functions plus manual per-task branching in `main()` (lines 718-773). A declarative task table (module + stage → function) driven by a loop would remove ~150 lines and make adding a third exchange additive rather than multiplicative (relates to REFACTOR-3 — do together).
- [ ] **STRUCT-2 (LOW-MEDIUM impact / medium effort)** — `pipelines/publish/data_validator.py` (621 lines, 18 methods) hand-lists which `check_*` methods to call per `run_curated_checks`/`run_bse_checks`/`run_dolt_checks`, making it easy to add a new check method but forget to register it. Consider a lightweight check-registry/decorator pattern.
- [ ] **BUG-8 (correctness, small effort, MEDIUM impact)** — `SymbolLinker.cross_reference_with_actions` (`pipelines/lineage/linker.py:204,245`) mutates the caller's `actions` DataFrame in place (`actions["_action_date"] = ...` then `drop(..., inplace=True)`), violating the explicit "never mutate input DataFrames" rule in `pipelines/lineage/CLAUDE.md`. If an exception is raised mid-loop, the caller's original DataFrame is left with a leaked `_action_date` column. Fix: `actions = actions.copy()` at the top, matching how `events` is already handled.

### Config/schema/doc consistency

- [ ] **DOC-1 (trivial fix, MEDIUM impact)** — `pipelines/extract/CLAUDE.md` states staging output is Parquet, but `extractor.py`/`bse_extractor.py` write `.csv` throughout. Either correct the doc now or resolve as part of IO-1's Parquet migration — currently misleads anyone reading the module doc before editing.
- [ ] **DOC-2 (small effort, LOW impact)** — Action-type vocabulary resolution is split across `field_mappings.yaml` and a 3-step fallback chain hardcoded in `bse_normalizer.py::normalize_bse_action_type` (exact match → substring match → NSE substring match via `FN.normalize_action_type`). Document the fallback chain explicitly in `field_mappings.yaml` comments or in `normalize/CLAUDE.md`.

### Dead code

- [ ] **CLEANUP-1 (trivial effort, LOW impact)** — `run.py::run_extract` (lines ~72-73, 81-82) still catches `NotImplementedError` with a "stub — skipping" warning for `fetch_bhavcopy`/`fetch_nse_corporate_actions`, but neither method raises `NotImplementedError` anymore (both are fully implemented). Safe to remove — leftover from an earlier stub phase.

### Test coverage gaps

- [ ] **TEST-1 (HIGH priority — mandated by CLAUDE.md)** — `pipelines/adjustments/CLAUDE.md` explicitly requires `tests/test_adjustments_factors.py` covering rights issues, face-value changes, duplicate events, and out-of-order recalculation; this file does not exist. BSE has a full test suite (`test_bse_adjustments.py` etc.) but core NSE modules lack equivalents: no `test_normalize_normalizer.py`, no `test_lineage_linker.py`/`test_lineage_rules.py`, and `test_extract_stale_fallback.py` covers only one extractor fallback path (no general `test_extract_extractor.py`).
- [ ] **TEST-2 (MEDIUM priority)** — `pipelines/publish/dolt_importer.py`'s core `import_all`/`load_table` path is untested beyond `test_dolt_importer_lineage_transform.py` and `test_dolt_importer_seed.py`; `filter_to_schema`, `resolve_action_type_ids`, and the CSV→Dolt row-count reconciliation path have no coverage.
