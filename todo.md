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

## Nice-to-have / deferred

- [ ] `releases/changelogs/` directory (blueprint calls for it alongside `releases/monthly/`).
- [ ] BSE coverage — explicitly out of scope for MVP, revisit at Enterprise tier demand.
- [ ] API-first delivery — deferred until Phase 3 or marketplace migration.
