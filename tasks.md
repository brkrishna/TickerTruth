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

### BUG-1 — `fact_symbol_lineage_event` column name mismatch (critical, FIXED — confirmed 2026-08-14)

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

**Confirmed fixed (2026-08-14, during the doc-cleanup pass):**
`dolt_importer.py::transform_lineage_events()` exists and does exactly this
column-rename mapping. Undated in the codebase's own history — no commit
reference found — but the fix is live and covered by
`tests/test_dolt_importer_lineage_transform.py`.

---

### BUG-2 — pandas ChainedAssignment FutureWarnings in normalizer (medium, FIXED — confirmed 2026-08-14)

**Symptom:** 8 `FutureWarning: ChainedAssignmentError` messages during `[normalize]` on every run.

**Affected lines:**
- `pipelines/normalize/normalizer.py`: lines 146, 150, 151, 157, 165, 168, 176, 183
- `pipelines/normalize/quality.py`: line 77

**Root cause:** Code uses `df["col"][indexer] = value` (chained indexing). pandas 3.0
Copy-on-Write makes this a silent no-op — assignments will stop taking effect.

**Fix:** Replace every chained assignment with `df.loc[indexer, "col"] = value`
or assign to a new DataFrame. Run `pytest` and verify no values are silently dropped.

**Files to change:** `pipelines/normalize/normalizer.py`, `pipelines/normalize/quality.py`.

**Confirmed fixed (2026-08-14):** `grep -n 'df\["[A-Za-z_]*"\]\['
pipelines/normalize/normalizer.py pipelines/normalize/quality.py` returns
no matches — the chained-indexing pattern this bug describes is gone.
(Separately, today's normalize test-coverage pass found and fixed a
*different* bug in the same two files — `.loc[:, col] = scalar` raising on
empty DataFrames — see the "normalize FIXED 2026-08-14" section further
down. Not a regression of BUG-2; a different pandas footgun in the same
files.)

---

### BUG-3 — `dim_exchange` and `dim_corporate_action_type` never populated (medium, FIXED — confirmed 2026-08-14)

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

**Confirmed fixed (2026-08-14):** went with the second option —
`dolt_importer.py::ensure_exchange_seeded()` and
`ensure_action_types_seeded()` exist and are called unconditionally at the
top of `import_all()`, before any table import.

---

### BUG-4 — Corporate actions fetch fails with no cached fallback (medium, FIXED — confirmed 2026-08-14)

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

**Confirmed fixed (2026-08-14):** `_stale_corp_actions_fallback()` exists
in `extractor.py` and is called from `fetch_nse_corporate_actions()` after
both the JSON API and Playwright fail — covered by
`tests/test_extract_stale_fallback.py`.

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

**Partial check (2026-08-14):** User pulled a PDF export of the Web
Analytics dashboard for the Aug 3–12 window, but it was the **Core Web
Vitals** panel (same one FOLLOWUP-1 already used) — not the Top
referrers / Top paths panel this follow-up actually needs. Those live on
the separate Traffic view of the same dashboard. Still open — no
referrer or path data collected yet.

One real observation surfaced anyway: the Core Web Vitals sample size
for the window is very thin — every chart's counts axis tops out at 10,
and only two URLs appear at all (`tickertruth.com/` and
`tickertruth.com/methodology`). That's a low real-user sample for a
10-day window with daily posts, so whatever Top referrers eventually
shows, expect small absolute numbers, not large ones.

**Still needed:** re-check the dashboard's Traffic/Top-referrers view
(not Core Web Vitals) for `linkedin.com` / `substack.com` rows and a
`/pricing` spike, per the original action items above. The 10-day run
also closed on 2026-08-14 (not 08-12 as originally scoped here — see
Day 9/10 reschedule in `docs/marketing-plan.md` §2) so the window to
check should extend through 08-14.

**Result (2026-08-18): user pulled the correct Traffic/Top-referrers
view — top referrer is `(none)`, not `linkedin.com` or `substack.com`.**
No confirmed click-through attribution from either platform for the
Aug 3–14 window.

**Likely cause, not yet verified:** every post in `content-queue.yaml`
links out as bare text — `tickertruth.com`, `tickertruth.com/pricing`,
`tickertruth.com/release-notes` — not a markdown/HTML hyperlink. LinkedIn
does auto-link plain URLs in feed posts, but routes the click through an
`lnkd.in` redirect (already seen on the Day 9 post, §3.9) which can drop
or rewrite the `Referer` header before the final hop lands on
tickertruth.com — Cloudflare would then log that hit as direct/`(none)`
even though the click genuinely came from LinkedIn. Substack normally
preserves referrer on outbound markdown links, so `(none)` covering both
platforms points more at a shared cause (redirect stripping, or genuinely
thin/no click-through volume — consistent with the small Core Web Vitals
sample already noted above) than at two independent failures.

**Not verified because:** dashboard access is required and this session
doesn't have it. To actually distinguish "LinkedIn's redirect stripped
the referrer" from "nobody clicked," check UTM-tagged links instead —
neither the LinkedIn nor Substack drafts use one now, and a raw domain
mention is the reason referrer data comes back empty regardless of
click volume.

**Closing this follow-up as answered — no referrer attribution recoverable
for the Aug 3–14 window itself** (the retroactive analytics tag is
already gone). Follow-up work, if wanted, is forward-looking: add UTM
parameters (`?utm_source=linkedin&utm_medium=social&utm_campaign=<day>`)
to the link text in future posts so click-through is attributable
per-platform, per-day, next time content goes out.

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

**REGRESSION found 2026-08-14 — the "left open" verification above never
happened, and the real-world result is a currently-broken nightly
pipeline (high, being fixed now).** Checked `gh run list
--workflow=nightly.yml` for the first time since the 2026-08-06 fix:
nightly ran successfully once (2026-08-07 00:55 UTC), then **every run
since has failed** (2026-08-07 21:06, 08-10, 08-11, 08-12, 08-13 — 5
consecutive failures). Confirmed via `gh run view <id> --log-failed`:

```
Restored existing Dolt state from remote.
error: Unable to add remote.
cause: remote already exists
##[error]Process completed with exit code 1.
```

**Root cause:** in the "Restore or bootstrap Dolt state from git remote"
step of `.github/workflows/nightly.yml`, the success branch runs `dolt
clone "$DOLT_REMOTE_URL" dolt_remote_state` and then, after moving
`.dolt` into place, redundantly runs `dolt remote add origin
"$DOLT_REMOTE_URL"` again — but `dolt clone` already configures `origin`
automatically as part of the clone. The second call fails outright
(`remote already exists`), which aborts the job with no fallback. This
line is only needed in the bootstrap (`else`) branch, where `dolt init`
creates a repo with no remote configured yet — it was almost certainly
copy-pasted into the wrong branch.

**Impact:** Dolt has not been refreshed via the nightly pipeline since
2026-08-07. Corp-actions/lineage/adjustment-factor data in Dolt has been
stale for a week, even though the INFRA-2 extract fix (below) now works
correctly when run manually. This was not caught by any of the "FIXED"
documentation above because the local dry-run testing used a `file://`
git transport where this failure mode doesn't reproduce identically
(needs confirming why, but likely dolt's clone-then-remote-add behavior
differs slightly by transport, or the local test never exercised the
restore-then-remote-add sequence exactly as CI does).

**Fix:** delete the redundant `dolt remote add origin "$DOLT_REMOTE_URL"`
line from the restore-success (`if`) branch — `dolt clone` already sets
it up. Being implemented now; see commit for details.

---

### INFRA-2 — `fetch_nse_corporate_actions()` blocked by Akamai (FIXED 2026-08-14 — original diagnosis was wrong)

**Original problem (2026-08-02, since corrected):** `www.nseindia.com`
was believed to be hard-blocked at Akamai's edge for every fetch method
(cookie handshake, JSON API, Playwright), on the theory that a 403 on
the homepage meant the network/IP was rejected outright, not fixable by
retrying, and needed proxy/vendor infrastructure to work around.

**Actual root cause (found 2026-08-14 while troubleshooting):** the 403
diagnosis on the homepage was real, but the conclusion drawn from it was
wrong. `requests.Session` stores `Set-Cookie` headers from a response
regardless of status code — the homepage 403 still sets Akamai's
anti-bot cookie (`AKA_A2`), and that cookie alone is sufficient to
authenticate `NSE_CORP_ACTIONS_API`. Manual `curl` and a live Python
repro both confirmed this: the API returns real, current corporate
action data (525 rows for a Jul 1 – Aug 13 2026 window) using nothing
but that cookie.

The actual reason `fetch_nse_corporate_actions()` was returning zero
rows for ~2 months: **the `brotli` package was never installed.** NSE's
API responses are Brotli-compressed (`Content-Encoding: br`); without
`brotli`/`brotlicffi` present, `requests` silently hands back undecoded
compressed bytes, and `.json()` raises `JSONDecodeError`
("Expecting value: line 1 column 1"). That error is indistinguishable
from a network/auth failure in the logs, which is exactly what led to
the original "hard block" conclusion.

A second, unrelated problem was also found in the same session: the
project's local `.venv` was stale — its `pip`/`python3` shebangs still
pointed at `/Users/ramarkrishna/apps/ICASHTL/.venv/...`, a path from
before the repo was renamed from ICASHTL to TickerTruth. `pip install`
commands were silently succeeding against system Python instead of the
venv (violates the global venv-only rule in `~/.claude/CLAUDE.md`).
Recreated via `rm -rf .venv && python3 -m venv .venv` — since `.venv/`
is gitignored, this was a local-only fix with no repo impact.

**Fix implemented (2026-08-14):**
- `requirements.txt` — pinned `brotli==1.2.0`, with a comment explaining
  why (NSE's Brotli-compressed responses silently failing `.json()`).
- `pipelines/extract/extractor.py` — `_get_session()` no longer treats a
  homepage 403 as a fatal/blocking condition (removed the
  `_homepage_blocked` flag entirely); it logs a warning and continues,
  since the session's cookies work regardless. `fetch_nse_corporate_actions()`
  no longer skips the Playwright fallback based on that flag — Playwright
  and the stale-cache fallback now always run on a JSON API failure, same
  as any other failure reason.
- `tests/test_extract_corp_actions_blocking.py` — rewritten to test the
  corrected behavior (403 doesn't prevent a usable session; Playwright is
  always attempted on API failure) instead of the old, incorrect
  block-detection behavior. Full suite passes (`pytest tests/ -q -m "not integration"`).
- `pipelines/extract/CLAUDE.md` — source-access notes corrected.
- Local venv recreated (see above); not a repo change.

**Live-verified 2026-08-14:** `fetch_nse_corporate_actions(from_date=2026-07-01, to_date=2026-08-13)`
returns 525 real rows end to end (cookie handshake → JSON API → validation → save).

**Residual bhavcopy issue — also FIXED (2026-08-14).** `fetch_bhavcopy()`
was failing for current dates (tested 2026-08-13 → HTTP 404) for a
reason unrelated to Akamai or brotli: NSE retired the old bhavcopy URL
pattern (`archives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip`)
for new dates — it still 200s for the old 2024-05-10 file, confirming a
URL/format migration, not a block. NSE moved to a new "UDiFF" bhavcopy
format at `nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip`,
with a different column schema (`TckrSymb`, `ClsPric`, `Sgmt`,
`FinInstrmTp`, etc. instead of `SYMBOL`, `CLOSE`).

Fix implemented in `pipelines/extract/extractor.py`:
- `_bhavcopy_url()` → `_bhavcopy_urls()`: now returns the new-format URL
  first, falling back to the legacy URL on a 404 (covers both current
  dates on the new format and older archive dates still only on the
  legacy one — live-tested, both 2026-08-13 new-format and 2024-05-10
  both actually resolve via the new URL, with the legacy URL as a
  defensive fallback for any date the new archive doesn't have).
- `_normalize_bhavcopy_columns()`: added UDiFF → canonical column
  aliases (`TCKRSYMB`→`SYMBOL`, `SCTYSRS`→`SERIES`, `OPNPRIC`→`OPEN`,
  `CLSPRIC`→`CLOSE`, `TTLTRADGVOL`→`TOTTRDQTY`, `TRADDT`→`TIMESTAMP`,
  etc.) — no filtering of non-equity segments, matching the existing
  (non-)filtering behavior for the legacy format.
- `tests/test_extract_bhavcopy.py` (new): covers URL ordering, the
  new→legacy fallback, the 404-from-both-formats failure path, and the
  UDiFF column mapping. All mocked, no live network calls.

**Live-verified 2026-08-14:** `fetch_bhavcopy(2026-08-13)` → 3,503 rows
via the new URL; `fetch_bhavcopy(2024-05-10)` → 2,710 rows, both through
the same code path with correct canonical columns.

Note: `fact_equity_eod` still won't populate end-to-end yet — there is
no `normalize` mapper from raw bhavcopy to `fact_equity_eod` in
`pipelines/normalize/normalizer.py` (only `dim_issuer`,
`dim_security_master`, and `fact_corporate_action_event` mappers exist
today). That's a separate, not-yet-scoped gap in the normalize stage,
not part of INFRA-2 (extract only).

**Follow-up — FIXED 2026-08-14.** Added `RawToCanonicalMapper.map_to_fact_equity_eod()`
in `pipelines/normalize/normalizer.py`, following the same
symbol-join-and-flag pattern as `map_to_fact_corporate_action_event()`.
Wired into the normal pipeline flow in `pipelines/run.py::run_normalize`
(Task 6) — reads `data/staging/bhavcopy_consolidated.csv`, writes
`data/curated/fact_equity_eod.csv`, which `DoltImporter` already had a
declared column mapping for (it was defined but never populated) and
loads last in `_IMPORT_ORDER`, after the other facts. `collect_stats()`
now reports `eod_rows` for release notes.

Per this module's null-handling rule (never drop rows silently), rows
with an unresolvable symbol or an unparseable trading date are retained
and flagged (`_quality_issues` / `normalization_error`) rather than
dropped — Dolt's `dolt table import --continue` (already used by
`DoltImporter.load_table`) skips rows violating NOT NULL/unique
constraints at import time, same as it already does for other facts.

Also fixed a related latent bug found while adding the empty-DataFrame
test required by `pipelines/normalize/CLAUDE.md`'s testing rules:
`QualityMetadata.add_quality_flags()` in `quality.py` used
`df.loc[:, col] = scalar` to add new columns, which raises `ValueError:
cannot set a frame with no defined index and a scalar` on a zero-row
DataFrame in the pandas version this project pins. This affected every
mapper (`map_to_dim_issuer`, `map_to_dim_security_master`,
`map_to_fact_corporate_action_event` too), not just the new one — none
of them had an empty-DataFrame test before now, so it went unnoticed.
Fixed by switching to plain column assignment (`df[col] = scalar`).

New tests: `tests/test_normalize_equity_eod.py` (happy path, empty
DataFrame, unresolved symbol, unparseable date, missing required
columns). Live-verified end-to-end against real NSE data
(`fetch_nse_symbols()` → `fetch_bhavcopy()` → `map_to_dim_security_master()`
→ `map_to_fact_equity_eod()`): 2,400 rows, 2,399 resolved to a
`security_id` (the one unresolved row is a non-equity instrument in the
bhavcopy — e.g. a gold bond — not present in `EQUITY_L.csv`, which is
expected). Full suite passes (`pytest tests/ -q -m "not integration"`),
`ruff check` clean.

---

## Open items — 2026-08-14 deep-dive survey

Broader repo survey done after the INFRA-2/fact_equity_eod work above,
looking for anything else open or stale. Findings not already covered
by a dedicated section:

### Test coverage gap — narrower than `session-handoff.md` implies (medium)

`session-handoff.md`'s "Open items" still frames the test suite as
starting near zero, which is stale — 14 test files exist today and BSE
is well-covered (`test_bse_extract.py`, `test_bse_normalize.py`,
`test_bse_lineage.py`, `test_bse_adjustments.py`, `test_bse_validator.py`).
The actual gap is **NSE core pure-function logic**:
- `pipelines/lineage/` (rename/merger/demerger/delisting detection,
  confidence scoring in `rules.py`/`linker.py`) — **zero NSE tests**.
- `pipelines/adjustments/` (split/bonus/reverse-split factor chains in
  `calculator.py`/`adjuster.py`) — **zero NSE tests**, despite
  `pipelines/adjustments/CLAUDE.md` explicitly requiring them.

These are two of the most correctness-critical modules in the product —
a wrong adjustment factor silently corrupts every backtest built on the
data — and neither has a single test today. `pipelines/normalize/` also
has a gap: only `test_normalize_equity_eod.py` exists for NSE; the core
`RawToCanonicalMapper` (`map_to_dim_issuer`, `map_to_dim_security_master`,
`map_to_fact_corporate_action_event`) and `quality.py` have no dedicated
test file (`test_normalize_normalizer.py` doesn't exist), which is also
how the `quality.py` empty-DataFrame bug (see the `map_to_fact_equity_eod`
writeup above) went unnoticed until now.

**lineage/adjustments FIXED 2026-08-14 (first pass).**
Added `tests/test_lineage_rules.py`, `tests/test_lineage_linker.py`,
`tests/test_adjustments_calculator.py`, `tests/test_adjustments_adjuster.py`
(84 new tests total). Two real bugs surfaced and fixed while writing to
the CLAUDE.md-required "determinism" and "no mutation" test cases —
neither had been exercised by any test before:

- **Lineage non-determinism (found via the required "same inputs →
  identical event list" test case).** `SymbolLinker.link_across_periods()`
  built its event list by iterating Python `set` differences
  (`current_syms - historical_syms`, etc.), whose iteration order for
  strings depends on the interpreter's hash seed (`PYTHONHASHSEED`,
  randomized per-process by default). Events sharing the same
  `event_date` — the common case, since a single run assigns one
  `period_date` to every inferred event — could therefore come out in a
  different relative row order across separate process runs (e.g. two
  different `nightly.yml` invocations) despite identical input snapshots.
  Confirmed empirically: running the same inputs under
  `PYTHONHASHSEED=1/2/3` produced three different row orderings before
  the fix. Fixed by adding a full deterministic tiebreaker to the final
  sort (`event_date`, `event_type`, `symbol_from`, `symbol_to` instead of
  `event_date` alone) in `pipelines/lineage/linker.py`. Verified fixed
  across the same three hash seeds, and covered by
  `test_link_across_periods_deterministic_across_hash_seeds` (spawns
  subprocesses with different `PYTHONHASHSEED` and diffs the output).
- Also found: renaming a symbol currently emits **two** events, not one —
  a RENAME (via the ISIN-match path on the removed side) and a LISTING
  (since the new symbol is, correctly, absent from the historical
  snapshot and the new-listing detector doesn't special-case rename
  targets). Not a bug per se — both events are individually accurate —
  but worth knowing about if a downstream consumer assumes one lineage
  event per real-world change. Documented via test, not changed.
- BUG-8 (below) fixed in the same pass, since it's in the same file and
  directly relevant to the "never mutate input DataFrames" test case.
- `pipelines/adjustments/adjuster.py` also got a one-line fix: its
  `pd.to_datetime(..., errors="coerce")` call raised a `UserWarning` on
  mixed/invalid date formats (surfaced by the new
  "unparseable event_date is dropped, not error" test) — switched to
  `format="mixed"` for the same coercion behavior with no warning, so
  `pytest -W error::UserWarning` now passes clean.
- Also confirmed and documented (not fixed — a design decision, not a
  bug) in the new test files' docstrings: `pipelines/adjustments/`'s
  actual implementation is narrower than its CLAUDE.md's aspirational
  spec — no RIGHTS, FACE_VALUE_CHANGE, MERGER/DEMERGER factor handling,
  no `confidence_flag` column, no `duplicate_group_id` dedup logic. The
  CLAUDE.md-required test cases that depend on those unimplemented
  features (Rights, Face value change, missing-date → UNRESOLVED flag,
  duplicate-event dedup) were not faked; only what's actually implemented
  is tested. Worth a decision later: implement the missing action types,
  or trim the spec to match reality.

Full suite (289 tests) passes with `pytest tests/ -q -m "not integration"
-W error::UserWarning`; `ruff check pipelines/lineage/ pipelines/adjustments/`
clean.

**normalize FIXED 2026-08-14 (second pass, same day).** Added
`tests/test_normalize_normalizers.py` (`FieldNormalizer` pure functions —
`normalize_ticker`, `normalize_company_name`, `normalize_date`,
`normalize_action_type`, `normalize_numeric`), `tests/test_normalize_quality.py`
(`QualityMetadata`), and `tests/test_normalize_normalizer.py`
(`RawToCanonicalMapper.map_to_dim_issuer`, `map_to_dim_security_master`,
`map_to_fact_corporate_action_event` — `map_to_fact_equity_eod` already had
its own file). 105 new tests. This closes the module's test gap entirely —
every public function in `normalizers.py`, `quality.py`, and `normalizer.py`
now has at least a happy-path, an edge-case, and an invalid-input test per
`pipelines/normalize/CLAUDE.md`'s testing rules.

Two more real bugs found and fixed by the required empty-DataFrame test
case, on top of the one already found in `quality.py` while building
`map_to_fact_equity_eod` (see above):

- **Three more `.loc[:, col] = scalar`-on-empty-DataFrame crashes**, the
  same pandas-version quirk as the `quality.py` bug — in
  `map_to_dim_issuer` (`pd.DataFrame(rows)` with `rows=[]` produced a
  zero-*column* DataFrame, not just zero rows, so `df["issuer_name"]`
  raised `KeyError` before the scalar-assignment issue even came up —
  fixed by constructing with explicit `columns=[...]`), and in
  `map_to_dim_security_master`/`map_to_fact_corporate_action_event`
  (`active_flag`, `record_date`, etc.). Rather than patch each call site,
  did a systematic pass converting every `df.loc[:, "col"] = ...` in
  `normalizer.py` (28 occurrences) to plain `df["col"] = ...` — behaviorally
  identical for populated DataFrames (verified: full suite + a live
  end-to-end run against real NSE data, 2,403 issuers / 2,406 securities,
  still pass), and immune to the empty-DataFrame crash. Row-indexed
  partial assignments (`df.loc[mask, "col"] = value`, e.g. the
  `active_flag` inactive-status override) were left untouched — only the
  whole-column `.loc[:, "col"]` pattern was affected.
- **`UNKNOWN_ACTION_TYPE` quality flag was dead code for every corporate
  action row, NSE and BSE, since this pipeline's inception.**
  `quality.py::_detect_issues` checked `row["ACTION_TYPE"]`, but neither
  `RawToCanonicalMapper.map_to_fact_corporate_action_event` nor
  `BSERawToCanonicalMapper.map_to_fact_bse_corporate_action_event` has
  ever produced a column by that name — both output `action_code`
  (confirmed via `grep`). So corporate action rows with an unrecognized
  action type were always scored as if clean (`_confidence_score = 1.0`,
  `confidence_flag = HIGH`) instead of being penalized 0.15 and flagged
  for review. Fixed by checking `action_code` instead. This is a genuine,
  silent data-quality gap that's been live in every release to date —
  worth a follow-up query against Dolt's `fact_corporate_action_event`
  for `action_code = 'UNKNOWN'` rows to see how many past releases were
  affected (not done as part of this fix).

Full suite (389 tests) passes with the same `-W error::UserWarning`
flag; `ruff check pipelines/normalize/` clean.

**extract FIXED 2026-08-14 (third and final pass, same day).** Added
`tests/test_extract_symbols.py` (`fetch_nse_symbols()`'s archives → JSON
API → legacy CSV fallback chain, `_normalize_symbol_columns`,
`_validate_symbols`), `tests/test_extract_corp_actions_normalize.py`
(`_date_chunks`, `_fetch_corp_actions_api`, `_normalize_corp_actions_columns`,
`_validate_corp_actions` — lower-level helpers not already covered by
`test_extract_corp_actions_blocking.py`'s control-flow tests), and
`tests/test_extract_consolidate.py` (`consolidate_to_staging`,
`_consolidate_source`, `_write_quality_report`, `_quality_warnings`,
including the `pipelines/extract/CLAUDE.md`-required idempotency test —
re-running consolidation on unchanged raw files produces identical
output). 39 tests, no new bugs found this pass.

Not covered: the Playwright browser-scraping fallback
(`_fetch_corp_actions_playwright`, `_pw_fill_date_filter`,
`_pw_extract_table_rows`) — would need a headless-browser test harness;
judged not worth the setup cost for a last-resort fallback whose
surrounding control flow (`fetch_nse_corporate_actions`'s decision to
call it, skip it, or fall through to stale-cache) is already exercised
by `test_extract_corp_actions_blocking.py`.

**This closes `TEST-1` (`todo.md`) entirely** — lineage, adjustments,
normalize, and extract (short of Playwright internals) all have real
test coverage as of today. Full suite: 428 tests, `ruff check
pipelines/extract/` clean.

### BUG-8 — `SymbolLinker.cross_reference_with_actions` mutates caller's input (FIXED 2026-08-14)

Logged in `todo.md` (opened 2026-07-03). `cross_reference_with_actions()`
assigned `actions["_action_date"] = ...` directly onto the caller's
`actions` DataFrame (later dropped via `actions.drop(..., inplace=True)`,
but a real mutation of the input in the interim — visible to any other
code holding the same reference, and left stray if an exception hit
between the assignment and the drop). Fixed by computing the parsed
dates into a local `action_dates` Series instead of assigning a column
onto `actions` at all — no functional change, `actions` is never
touched. Covered by
`test_cross_reference_does_not_mutate_actions_input` and
`test_cross_reference_does_not_mutate_lineage_events_input` in
`tests/test_lineage_linker.py`.

### BUG-9 — Release notes summary always shows `Dolt Commit: N/A` (low)

Opened 2026-08-15, found while verifying the first real `release.yml`
run after BUG/INFRA fixes below (`v2026.08.15`, `releases/monthly/v2026.08.15.md`).
The release notes template's `**Dolt Commit:**` field never resolves to
an actual commit hash — it's hardcoded or falls through to `N/A` in
every release generated so far, including this one. Per `dolt/CLAUDE.md`
and `docs/CLAUDE.md`'s release-notes format rules, this field exists so
a subscriber can pin to a specific Dolt commit for point-in-time
queries; as `N/A` it's dead weight. Needs `pipelines/publish/release_notifier.py`
(or wherever the template is rendered) wired up to read the actual Dolt
commit hash produced by the `load` stage. Not yet investigated further
— no root cause identified, just confirmed the field is empty on a real
release.

### BUG-10 — `fact_symbol_lineage_event` showed 0 new events on a release with 777 corporate actions (low, needs verification)

Opened 2026-08-15, same `v2026.08.15` release as BUG-9. The release
summary reported "Lineage events detected: 0" alongside 777 ingested
corporate actions and 19 adjustment factor rows — plausible if none of
those actions were renames/mergers/delistings, but not yet confirmed
either way. Needs a spot-check against `fact_symbol_lineage_event.csv`
on the `curated-data` branch (or a rerun of `SymbolLinker.link_across_periods`
against the same input) to confirm 0 is correct and not a silent
pipeline gap — e.g. `lineage` task not receiving the right prior-period
snapshot to diff against now that `curated-data` persistence actually
works (see INFRA-1 and the `nightly.yml`/`release.yml` gitignore fixes
the same day). Not yet investigated.

### Stale documentation found during the survey (low, but misleading)

- Top-level `CLAUDE.md`'s "Open work (as of 2026-06-15)" section still
  says "BSE Symbol Master & Lineage expansion — phases B1–B8 defined in
  `todo.md`; nothing implemented yet." This is wrong: `todo.md` and
  `git log --oneline -- '*bse*'` confirm phases B1–B7 are complete (7
  commits, dedicated `bse_extractor.py`, `bse_normalizer.py`,
  `bse_scrip_history.py`, `isin_bridge.py`, `bse_adjuster.py` modules
  plus 5 BSE test files). Only B8 (commercial packaging — pricing SKU,
  entitlement gating) is genuinely incomplete. Worth correcting so a
  future session doesn't waste time re-discovering BSE work that already
  exists, or re-reads a stale "not started" note as current.
- `dolt/CLAUDE.md`'s "CI persistence" section describes the git-remote
  mechanism as working with no caveat — now inconsistent with the
  INFRA-1 regression documented above until that's fixed and re-verified.
- `session-handoff.md`'s "Next suggested task" (write the initial test
  suite) is stale in framing, even though its underlying point (test
  coverage gap) is still correct in substance — see above.

**Not yet started** (doc corrections only, no code risk — low priority
relative to INFRA-1 regression and the lineage/adjustments test gap).

---

## Progress tracking notes

- Track failures and manual effort per release
- Capture scope changes or boundary exceptions
- Note when a task moves from manual to automated
