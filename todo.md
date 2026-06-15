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

### Phase B1 — Data source audit & schema design

- [ ] Audit all publicly available BSE data feeds:
  - Equity master (`EQ` and `SME` segments) — scrip code, short name, full name, ISIN, listing date, status
  - Daily bhavcopy (EQ segment CSV) — OHLCV keyed by scrip code
  - Corporate actions feed — bonus, split, dividend, rights, merger, delisting
  - Historical security master (scrip code renames, code reassignments, delistings)
- [ ] Map BSE scrip code lifecycle: document how BSE handles renames, suspensions, delistings, and re-listings vs NSE's symbol rename approach
- [ ] Design schema extensions for BSE tables (new columns, new tables, ISIN-bridge table) — **ask before touching any existing NSE schemas**
- [ ] Identify gaps: BSE data fields with no NSE equivalent (and vice versa) that affect lineage or adjustment logic

### Phase B2 — BSE extract pipeline

- [ ] Add `pipelines/extract/bse_equity_master.py` — download and parse BSE equity master (scrip code, ISIN, name, segment, listing date, status)
- [ ] Add `pipelines/extract/bse_bhavcopy.py` — download daily BSE EQ bhavcopy, validate schema, store raw
- [ ] Add `pipelines/extract/bse_corporate_actions.py` — scrape / download BSE corporate action announcements (parse bonus ratio, split ratio, dividend amount, record date, ex-date)
- [ ] Add `pipelines/extract/bse_security_history.py` — pull historical changes to scrip master (scrip code reassignments, delistings, name changes) from available BSE archives
- [ ] Wire all four extractors into `pipelines/run.py` behind a `--exchange bse` or `--tasks bse_extract` flag so NSE-only runs are unaffected

### Phase B3 — BSE normalize pipeline

- [ ] Add `pipelines/normalize/bse_symbol_aliases.py` — canonicalize BSE scrip names (handle trailing whitespace, encoding issues, short name vs full name variants) mirroring the pattern in `symbol_aliases.py`
- [ ] Add `pipelines/normalize/bse_corporate_actions.py` — parse and clean BSE action events into the same normalized schema used for NSE (`action_type`, `ratio`, `amount`, `record_date`, `ex_date`, `confidence_flag`)
- [ ] Extend `quality.py` `score_to_flag()` to handle BSE-specific confidence signals (BSE announcements often lack ex-date; flag accordingly)
- [ ] Write unit tests in `tests/test_bse_normalize.py` covering name canonicalization, action parsing, and confidence scoring edge cases

### Phase B4 — BSE lineage pipeline

- [ ] Add `pipelines/lineage/bse_scrip_history.py` — reconstruct per-scrip timeline of name changes, status changes (active → suspended → delisted), and scrip code reassignments
- [ ] Handle BSE-specific edge cases: scrip codes retired and reassigned to a different company (rarer than NSE symbol reuse but documented)
- [ ] Produce `bse_scrip_lineage` curated table: one row per (scrip_code, effective_from, effective_to) interval with scrip name, ISIN, segment, status
- [ ] Add regression tests in `tests/test_bse_lineage.py` for known historical renames and delistings (seed a small fixture set from real BSE history)

### Phase B5 — NSE–BSE cross-exchange reconciliation (ISIN bridge)

- [ ] Add `pipelines/lineage/isin_bridge.py` — join NSE symbol history and BSE scrip history on ISIN to produce a unified cross-exchange entity table
- [ ] Produce `exchange_security_map` table: ISIN → (nse_symbol, nse_effective_from, nse_effective_to, bse_scrip_code, bse_effective_from, bse_effective_to)
- [ ] Flag ISINs that appear on BSE but never on NSE (BSE-only listings) — these are new rows buyers get only with BSE coverage
- [ ] Flag ISINs with conflicting corporate action dates across exchanges (data quality signal, high buyer value)
- [ ] Add `tests/test_isin_bridge.py` with fixture cases: dual-listed, BSE-only, NSE-only, delisted from one exchange only

### Phase B6 — BSE adjustment factors

- [ ] Extend `pipelines/adjustments/factors.py` to compute split/bonus adjustment factors from BSE corporate actions using the same `compute_adjustment_factor()` logic
- [ ] Validate BSE adjustment factors against NSE factors for dual-listed securities — discrepancies signal a data quality issue in either feed
- [ ] Add `tests/test_bse_adjustments.py` mirroring the NSE adjustment test suite

### Phase B7 — Validation, QA & release integration

- [ ] Extend `pipelines/publish/validate.py` to include BSE table row-count checks, ISIN bridge completeness checks, and cross-exchange action-date consistency checks
- [ ] Gate BSE Dolt commits on passing validation (same pattern as BUG-7 fix for NSE)
- [ ] Update `pipelines/run.py` orchestrator to include BSE stages in the standard run and `--dry-run` path
- [ ] Update monthly release packaging to include BSE tables as optional add-on artifact (separate tarball or Dolt branch `bse/`)
- [ ] Add BSE coverage section to `docs/methodology.md` and `docs/data-dictionary.md`

### Phase B8 — Commercial packaging & go-to-market

- [ ] Define BSE add-on SKU: price relative to NSE base (e.g., +40–60% for BSE bundle, or separate BSE-only tier)
- [ ] Update subscriber delivery scripts to gate BSE artifacts behind the BSE-tier entitlement check
- [ ] Add "BSE Coverage" section to the website landing page and sample-queries page
- [ ] Create one marketing notebook: `notebooks/bse_nse_dual_listing_reconciliation.ipynb` — show how ISIN bridge catches conflicting corporate action dates across exchanges
- [ ] Draft 1–2 LinkedIn posts: "BSE-only listings your backtest is missing" and "When NSE and BSE disagree on the record date"
- [ ] Offer BSE coverage as an upsell in first pilot customer conversations

---

## Nice-to-have / deferred

- [ ] `releases/changelogs/` directory (blueprint calls for it alongside `releases/monthly/`).
- [ ] API-first delivery — deferred until Phase 3 or marketplace migration.
