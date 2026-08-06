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

## Follow-ups

### FOLLOWUP-1 — Verify Cloudflare Web Analytics is capturing data (opened 2026-08-04, RESOLVED 2026-08-06)

**Context:** The beacon token previously embedded on all 6 landing pages and the
blog footer partial (`4cf86be656924547a93bfba532bc23bc`) wasn't showing any
visits in the Cloudflare Web Analytics dashboard, despite the script tag being
live in production. Root cause not diagnosed — token may have been stale,
mistyped, or never actually attached to a live Web Analytics site in the
dashboard.

**Action taken:** Swapped the token across all 7 files
(`website/landing-page/{index,pricing,methodology,sample-queries,release-notes,contact}.html`,
`website/blog/layouts/partials/footer.html`) to `5e7540b0c0d541d59248c1e3f9e3a08f`
and pushed to `main` (commit `fec069f`) — Cloudflare Pages auto-deployed.

**Resolution (2026-08-06):** Confirmed via the Core Web Vitals panel in the
dashboard — real-user LCP/INP/CLS samples are now populating against actual
page paths (`/`, `/release-notes`, `/blog/`, `/pricing`, `/sample-queries`,
`/methodology`, three blog posts), with data points from Aug 2 onward. The
beacon is firing correctly under the new token. All CWV metrics are in the
"Good" band (LCP P50 582ms / P75 676ms / P90 840ms / P99 909ms). Full writeup
in `docs/marketing-plan.md` §6. `docs/cloudflare-analytics.md` was checked
against this finding — no caveats needed updating.

**Left open, tracked separately:** the Core Web Vitals panel doesn't surface
visit counts or top referrers, so LinkedIn/Substack attribution for the 10-day
content run is still unconfirmed — see `FOLLOWUP-2` below.

---

### FOLLOWUP-2 — Confirm referrer attribution for the 10-day content run (opened 2026-08-06)

**Context:** `FOLLOWUP-1` confirmed the Web Analytics beacon is capturing
real visits (via the Core Web Vitals panel), but that panel doesn't show
visit counts, top referrers, or top paths — so it's still unconfirmed
whether the Day 1–4 LinkedIn (`urn:li:activity:7489909231228403712`,
`...7490250295906779136`, `...7490642030671470592`, `...7491006111534432256`)
and Substack (`tickertruth.substack.com/p/the-graveyard-problem-survivorship`,
plus Days 1–3) posts are actually driving click-throughs, as opposed to
staying as impressions on the platform itself.

**Action needed:**
- In the Web Analytics dashboard, check the **Top referrers** panel
  (`dash.cloudflare.com` → Analytics & Logs → Web Analytics → tickertruth.com),
  filtered to the Aug 3–12 window, for `linkedin.com` and `substack.com`
  entries
- Cross-check **Top paths** for a `/pricing` spike correlated with a specific
  day's post, per the "Reading it against what actually matters here" section
  of `docs/cloudflare-analytics.md`
- Once the 10-day run completes (2026-08-12), roll this into the Day-28 sprint
  review metrics mentioned in `docs/marketing-plan.md` §4.5
  (`docs/marketing/content-log.csv`)

---

## Infrastructure — pipeline release blockers

Both items were blocking a real (non-security-master-only) monthly
release; see `session-handoff.md` §"(2026-08-02) Data/release catch-up"
for the original findings. INFRA-1 is fixed (2026-08-06); INFRA-2 is
still research/options only, no code changes made.

### INFRA-1 — Dolt state has no durable persistence (high, FIXED 2026-08-06)

**Problem:** `nightly.yml` runs `dolt init` fresh on every ephemeral CI
runner and never pushes the result anywhere. `dolt/.dolt` and
`data/curated/` are gitignored, so each nightly run's Dolt commits are
discarded when the runner is torn down. `release.yml` then fails because
it needs `data/curated` from a prior `load` step but runs on a fresh
checkout with nothing there — this has been failing since 2026-06-02.
A stopgap (`workflow_dispatch`-only artifact upload of `dolt/.dolt` +
`data/curated`, 7-day retention) exists but isn't part of the scheduled
cron path and isn't a real fix.

**Options considered:**

1. **DoltHub remote (recommended).** DoltHub is a hosted Dolt remote —
   `dolt remote add origin <dolthub-url>` / `dolt push origin main` /
   `dolt clone` from CI, the same push/pull model as git. Free tier
   covers public repos. This is the standard, Dolt-native way to solve
   exactly this problem, and it doubles as a future subscriber-access
   mechanism: `todo.md`'s "Commercial delivery" section already lists
   "Private DoltHub repo access for paying subscribers" as one of the
   candidate delivery models, so setting this up now solves both the CI
   persistence gap and gives the private-repo option a real backend to
   evaluate later. Downside: introduces a dependency on a third-party
   hosted service and (for a private repo, if the free public tier isn't
   acceptable for pre-release data) a paid plan.
2. **Git remote support in Dolt (new, v1.81.10, Feb 2026).** Dolt can now
   use a plain Git host (GitHub, GitLab, Bitbucket) as a Dolt remote —
   `dolt remote add origin https://github.com/<org>/<repo>.git` — storing
   Dolt's chunk data on a custom ref (`refs/dolt/data`) that doesn't
   touch the normal git history or show up in GitHub's UI. In CI:
   `dolt clone "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" db`
   needs no extra secret beyond the default `GITHUB_TOKEN`. This would
   let the *same* GitHub repo TickerTruth already lives in double as the
   Dolt remote — no new account/service. Caveats: very new (one DoltHub
   blog post as the only documentation found), and there's a known bug
   in v1.81.10 when the local `git` binary needs credentials via STDIN
   (shouldn't affect GitHub Actions' token-based auth, but worth
   confirming against whatever Dolt version is actually pinned in CI
   before relying on it). Worth prototyping before DoltHub given it needs
   zero new infra, but the newness is a real risk for something a
   monthly release depends on.
3. **GitHub Actions cache as a stopgap.** `actions/cache`, keyed on a
   rolling key, could persist `dolt/.dolt` between nightly runs without
   any external service. Simple, zero new accounts. But caches are
   evicted after 7 days of disuse and are capped per-repo (10GB) —
   acceptable as a bridge, not as the permanent answer, and doesn't help
   `release.yml` if a cache miss happens to land on release day.
4. **Self-hosted AWS-backed Dolt remote** (`aws://[dynamo-table:bucket]/db`).
   Ruled out: needs a real AWS account with both S3 and DynamoDB, more
   infra to own than DoltHub for no clear benefit here, and the project's
   existing cloud footprint is Cloudflare (R2), not AWS — R2 is
   S3-compatible for blob storage but Dolt's AWS remote backend also
   needs DynamoDB for chunk manifests, so R2 doesn't drop in as a
   substitute.

**Recommendation (superseded by fix below):** DoltHub was the original
recommendation, but option 2 (git-remote support) was implemented instead
after confirming it actually works with the Dolt version installed
locally (`dolt version` → 2.0.8) — verified end-to-end against a local
bare git repo before touching CI: `dolt init` → `dolt remote add origin
<git-url>` → `dolt push origin main` → `dolt clone <git-url>` from a
second location round-trips correctly, and `dolt push origin <tag-name>`
propagates tags the same way. No DoltHub account needed for this fix.

**Fix implemented (2026-08-06):**
- `.github/workflows/nightly.yml` — replaced the unconditional `dolt init`
  with a restore-or-bootstrap step: `dolt clone` the repo's own git remote
  (`refs/dolt/data`, via `GITHUB_TOKEN`) to recover the previous run's
  state, falling back to `dolt init` + schema + initial push only if the
  remote has no Dolt data yet (first run ever). After the pipeline's
  `load` step, a new step pushes `main` plus every local tag (nightly
  tags every successful commit `vYYYY.MM.DD` per
  `pipelines/run.py::run_load`, so the branch push alone wasn't enough).
  `permissions: contents: read` → `write` to allow the push.
- Separately, `data/curated/*.csv` (needed by `release.yml`'s `export`
  task, also gitignored) is persisted via a plain git branch
  (`curated-data`) rather than reconstructed from Dolt tables — Dolt's
  imported schema drops/renames columns relative to the original curated
  CSVs (`dolt_importer.py`'s `_TABLE_COLUMNS`), so round-tripping through
  Dolt isn't guaranteed lossless. `nightly.yml` pushes to this branch
  after every successful run; `.github/workflows/release.yml` now
  restores it (`git checkout origin/curated-data -- data/curated`) before
  running `export`, which is the direct fix for the release.yml failures
  logged since 2026-06-02.
- Documented the mechanism in `dolt/CLAUDE.md` under a new "CI
  persistence" section, including why DoltHub was deferred rather than
  ruled out (still the right call if/when private subscriber-facing Dolt
  access is needed — see `todo.md`'s "Commercial delivery" section).

**Verified:** YAML validity (`python3 -c "import yaml..."`) and
`actionlint` (shellcheck-backed) on both workflow files — clean except
pre-existing warnings in code this change didn't touch. The clone/push/tag
round-trip and the curated-data branch restore/push logic were both
dry-run tested locally against throwaway bare git repos before being
wired into the real workflows (not run against GitHub Actions itself —
that only happens on the next real `nightly.yml` trigger).

**Left open:** the first real nightly run against GitHub's actual
`https://` git transport (vs. the `file://` transport used for local
testing) is unverified — worth a manual `workflow_dispatch` trigger and a
check of the Action's logs before trusting the next scheduled run.

---

### INFRA-2 — `fetch_nse_corporate_actions()` blocked by Akamai (high)

**Problem:** `www.nseindia.com` returns HTTP 403 "Access Denied" from
Akamai's edge for every fetch method the extractor tries (cookie
handshake, JSON API, Playwright), both from this local network and from
GitHub Actions runners. Confirmed via direct `curl`/`requests` testing
on 2026-08-02 — not a header/TLS-fingerprint bug, not fixable by
retrying. No `nse_actions_*.csv` files exist in `data/raw/` at all.
Bhavcopy fetching is affected the same way (814+ days stale, last
success 2024-05-10) since it hits the same domain.

**Options considered:**

1. **Residential proxy provider (recommended as the near-term fix).**
   Akamai's bot detection weighs IP reputation heavily — datacenter IPs
   (GitHub Actions runners, most home-network egress in some regions)
   are flagged far more aggressively than residential IPs. Providers
   with India-specific residential pools: Bright Data, Oxylabs, Decodo
   (formerly Smartproxy), IPRoyal, DataImpulse, SOAX — 2026 pricing runs
   roughly $1.75–$8.50/GB depending on tier and volume commitment.
   Because the actual payload here is tiny (a handful of CSVs per day,
   likely well under 1GB/month total), even the priciest per-GB tier
   costs a few dollars a month — this is a cheap fix if it works, and
   doesn't require any code beyond adding proxy credentials to the
   existing `requests`/Playwright config. Risk: proxy IPs can themselves
   get blocklisted over time with sustained scraping, so this needs
   monitoring, not a one-time setup.
2. **Licensed NSE data vendor (recommended as the durable fix).** NSE
   itself sells a paid EOD historical data subscription directly
   (`nseindia.com/static/market-data/eod-historical-data-subscription`,
   contact `marketdata@nse.co.in`) — bhavcopy plus, per the page,
   corporate/security detail. This is the actual authoritative source,
   delivered through a proper subscription channel rather than scraping,
   so it sidesteps the Akamai problem entirely rather than working around
   it. Separately, NSE-authorized redistributors — TrueData and
   GlobalDatafeeds (GDFL) — offer API access to real-time and historical
   NSE/BSE/MCX data as licensed vendors; worth a pricing/coverage
   comparison against NSE's own subscription once actual corporate-action
   history coverage (not just EOD price) is confirmed for each. This is
   the more defensible long-term choice for a product whose entire pitch
   is data trustworthiness/provenance — "sourced via residential proxy
   scraping" is a worse footnote in `docs/methodology.md` than "licensed
   subscription."
3. **Cloud VM in an Indian region (e.g. AWS `ap-south-1`, DigitalOcean
   Bangalore) instead of GitHub-hosted runners.** Considered but likely
   insufficient alone: Akamai's block appears to be reputation-based
   (datacenter vs. residential), not purely geographic, so a datacenter
   IP in Mumbai is still a datacenter IP and may get flagged the same as
   a US-based GitHub Actions runner. Would need testing to confirm either
   way before relying on it, and it adds infra (a VM to keep patched and
   running) that a proxy subscription avoids.
4. **Broker API (Zerodha Kite Connect) as a data source.** Kite Connect's
   data APIs are ~₹500/month, order/account APIs free since March 2025 —
   but this is an execution/quotes API for a live trading account, not
   positioned as a corporate-actions/reference-data feed, and typically
   requires an active demat/trading account tied to a real person, which
   doesn't fit a backend service cleanly. Not pursued further as a
   primary source; possibly worth a cross-check for adjustment-factor
   validation only.

**Recommendation:** short-term, trial a residential proxy (small spend,
no vendor contract, fast to test) to unblock nightly extraction while
evaluating; in parallel, get pricing/coverage details from NSE's own
paid subscription and from TrueData/GlobalDatafeeds, since a licensed
vendor is the right permanent source for a product whose value
proposition depends on data provenance being clean.

**Next step (not yet done):** email `marketdata@nse.co.in` for the
official subscription's actual coverage (does it include corporate
actions, not just EOD bhavcopy?) and pricing; get quotes/trial access
from TrueData and GlobalDatafeeds; separately, sign up for a small proxy
trial (e.g. IPRoyal or DataImpulse, budget tier) and test one fetch cycle
against `nseindia.com` to confirm the 403 actually clears before
committing to a subscription either way.

---

## Progress tracking notes

- Track failures and manual effort per release
- Capture scope changes or boundary exceptions
- Note when a task moves from manual to automated
