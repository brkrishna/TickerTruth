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
