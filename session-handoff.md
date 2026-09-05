# Session handoff

## Status
All five implementation phases are complete (phases 1–5 committed).

## What was built
- `pipelines/extract/extractor.py` — fetches NSE equity master, bhavcopy, corporate actions
- `pipelines/normalize/` — normalizer.py, normalizers.py, quality.py, field_mappings.yaml
- `pipelines/lineage/` — rules.py (LineageRulesEngine), linker.py (SymbolLinker)
- `pipelines/adjustments/` — calculator.py, adjuster.py, validator.py
- `pipelines/publish/` — dolt_importer, data_validator, sample_generator, packager,
  manifest_builder, access_manager, release_notifier, warehouse_exporter
- `pipelines/run.py` — end-to-end orchestrator (extract → normalize → lineage → adjust →
  validate → load → export → manifest → release-notes)
- `dolt/schema.sql` — full DDL; Dolt repo initialized at `dolt/`
- `website/` — Cloudflare Worker (`website/public/`, `src/index.js`, `wrangler.jsonc`) landing page and docs mirror; migrated from Cloudflare Pages 2026-09-05
- `.github/workflows/` — ci.yml only (nightly.yml, release.yml removed 2026-09-05, see dated entry below)
- First release tagged: `v2026.06.01`

## Open items
- (2026-08-14) Test suite is no longer a gap — see the dated section at the
  bottom of this file. `dolt_importer.py`'s core import path and the
  Playwright scraping fallback are the remaining coverage holes
  (`todo.md` TEST-2 and the extract test writeup in `tasks.md`).
- `dolt/migration/` and `dolt/tags/` subdirectories are documented as planned but not yet created.
- `docs/schema-reference.md` and `docs/faq.md` are planned but not yet written.
- (2026-07-23) `main` now has branch protection requiring 1 approving review.
  `release.yml`'s bot push to `main` bypasses this automatically once the
  `RELEASE_BOT_PAT` repo secret (a fine-grained PAT from an admin account,
  Contents + Pull requests: write) is added — falls back to opening a PR
  needing manual merge until then. `nightly.yml` no longer pushes to `main`
  at all (see below), so it's unaffected.
- (2026-07-23) `nightly.yml` scope changed: it now only runs
  `extract,normalize,lineage,adjust,validate,load` (keeps Dolt current daily
  on trading days). The public release — `export,manifest,release-notes,
  website` plus R2 sample upload — happens only via `release.yml` on a
  version tag (monthly cadence), since that's the actual cadence customers
  receive and it avoids fighting branch protection every night.

## Next suggested task (updated 2026-08-14 — the version below is stale)
~~Write the initial test suite...~~ Done — see the 2026-08-14 section at
the bottom. Next real priorities, in order: (1) confirm tonight's
`nightly.yml` run actually goes green (`gh run list --workflow=nightly.yml`
— it's been failing since 2026-08-07, fixed today but unverified against a
real scheduled trigger), (2) `todo.md` TEST-2
(`dolt_importer.py::import_all`/`load_table` core path is still untested),
(3) whatever `todo.md`'s REFACTOR-*/PERF-*/IO-*/STRUCT-* backlog items look
highest-value once (1) and (2) are settled.

## (2026-08-02) Data/release catch-up — findings and open bugs

Pushed release `v2026.08.02` (security master only — see
`releases/monthly/v2026.08.02.md` for full disclosure). While doing this,
found several real problems that need follow-up:

- **`fetch_nse_corporate_actions()` is broken** (`pipelines/extract/extractor.py`).
  Root cause confirmed (2026-08-02, via `curl`/`requests`): `www.nseindia.com`
  returns HTTP 403 "Access Denied" from Akamai's edge for this network — both
  locally and in GitHub Actions CI. Not a header/TLS-fingerprint issue, not
  fixable by retrying. **This is an infrastructure problem (needs a different
  egress IP/proxy or a licensed NSE data vendor), not a code bug** — so it
  has NOT been "fixed" in the sense of restoring live data. What *was* fixed
  (commit `f834588`): the extractor now detects the 403 explicitly, skips
  the Playwright fallback (which was hitting the same blocked domain and
  burning 30-60s for nothing), logs at ERROR instead of WARNING, and raises
  a RuntimeError that names the real cause. Because `run.py` still treats
  extractor failures as non-fatal, `nightly.yml` has been reporting "success"
  every weekday while silently ingesting **zero corporate actions** for some
  unknown period — check how far back this goes. Corp
  actions/lineage/adjustment-factor data has likely been stale/empty in Dolt
  for a while. Next step is the infra decision (proxy/vendor), not more code.
- **`nightly.yml` never persists Dolt state — FIXED 2026-08-06.** It used
  to do `dolt init` fresh every run and never push/upload it, so daily
  "refreshes" were being discarded, not accumulated. Fixed using Dolt's
  git-remote support: `nightly.yml` now clones the repo's own git remote
  (`refs/dolt/data`) to restore prior state, and pushes `main` + tags back
  after `load`. `data/curated` (needed by `release.yml`) is separately
  persisted via a `curated-data` git branch. Full writeup in `tasks.md`
  INFRA-1 and `dolt/CLAUDE.md`'s "CI persistence" section. Caveat: verified
  locally against a `file://` git remote, not yet against a real nightly
  run on GitHub Actions — check the next scheduled/dispatched run's logs.
- ~~**Bhavcopy is 814+ days stale**~~ — FIXED 2026-08-14, see below.
- Local Dolt repo's pre-2026-08-02 commit history (May 31–June 2) was lost
  during this session (accidental `rm -rf dolt/.dolt` before confirming) —
  low impact since it only held dimension-table snapshots, no unique fact
  data, and was never pushed to a remote. Local Dolt now starts fresh from
  `v2026.08.02`.
- No git tags currently exist in this repo (`git tag -l` is empty) despite
  `release.yml` being tag-triggered — releases have apparently always been
  done via direct commits to `main`, not tag pushes.

Suggested priority: Dolt/curated-data persistence is now fixed (see
INFRA-1 above) — `fetch_nse_corporate_actions()` (INFRA-2 in `tasks.md`,
options documented but not yet implemented) is the remaining blocker
before the next real monthly release.

## (2026-08-14) INFRA-2 — corrected, FIXED, not what it looked like

The "Akamai hard block" diagnosis above was wrong — no proxy or vendor
needed. Root cause was a missing `brotli` package causing `.json()` to
fail on NSE's Brotli-compressed API responses, which looked identical to
a network block in the logs. Full writeup and fix in `tasks.md` INFRA-2.
`fetch_nse_corporate_actions()` is live-verified working
(525 rows fetched for a 6-week window). Also found and fixed: the local
`.venv` was stale, pointing at a pre-rename `ICASHTL` path, so `pip
install` was silently landing in system Python — recreated, no repo
impact since `.venv/` is gitignored.

`fetch_bhavcopy()` — separate issue, NSE migrated to a new bhavcopy
URL/format ("UDiFF") that the extractor didn't support. Not an
Akamai/brotli issue. **Also FIXED 2026-08-14**, same session: tries the
new URL first, falls back to the legacy one. Live-verified: 3,503 rows
for 2026-08-13, 2,710 rows for the old 2024-05-10 archive date, both
through the same code path. `fact_equity_eod` also went from
never-populated to live: added `RawToCanonicalMapper.map_to_fact_equity_eod()`
and wired it into `run.py::run_normalize`. Full writeup in `tasks.md`
INFRA-2.

## (2026-08-14) Test coverage + a broken nightly pipeline, same day

Three things happened in this session, in order:

1. **INFRA-2 fixed** (corp actions + bhavcopy, see above and `tasks.md`).
2. **Found `nightly.yml` had been silently failing every run since
   2026-08-07** — a leftover `dolt remote add origin` after `dolt clone`
   (which already sets it up) failed with `remote already exists` and
   aborted the job. Fixed; not yet verified against a real scheduled run
   (next one fires ~20:30 UTC tonight — check `gh run list
   --workflow=nightly.yml`). Full writeup: `tasks.md` INFRA-1.
3. **Closed the entire test-suite gap** this file used to call the
   highest-priority open item. `pipelines/lineage/`, `pipelines/adjustments/`,
   `pipelines/normalize/`, and `pipelines/extract/` (NSE) all went from
   zero-or-thin coverage to real tests across four passes — 428 tests
   total, up from 214 at the start of the day. Found and fixed five real
   bugs along the way purely by writing the test cases each module's own
   `CLAUDE.md` already required: a hash-seed-dependent non-determinism bug
   in `SymbolLinker`, a DataFrame-mutation bug (BUG-8, `todo.md`), two
   classes of empty-DataFrame crashes, and a dead `UNKNOWN_ACTION_TYPE`
   quality check that's never fired for any corporate action row in this
   pipeline's history (checked a column name neither the NSE nor BSE
   mapper has ever produced). Full writeup per module in `tasks.md`; BSE
   status and BUG-1 through BUG-4 were also confirmed fixed and marked as
   such in `tasks.md`/`todo.md` (they'd been fixed in earlier sessions but
   never marked). Also corrected two stale docs: top-level `CLAUDE.md`'s
   BSE "nothing implemented" note (phases B1–B7 are done) and
   `pipelines/extract/CLAUDE.md`'s Parquet-vs-CSV claim (`todo.md` DOC-1).

## (2026-08-22) `nightly.yml` 8-21 run failure — root cause was a real data bug, not infra

`nightly.yml` runs 8-17 through 8-20 were green (confirming INFRA-1's fix
holds); the 8-21 run failed at the `adjust` stage: "1 duplicate
(security_id, as_of_date) rows in adjustment output". Because both push
steps in `nightly.yml` are gated `if: success()`, nothing from that run
was pushed — no data was lost, just not advanced.

Root cause, reproduced locally against live data: NSE reported two
"Scheme Of Arrangement - Bonus Ncrps X:Y" events (preference-share
issuance) for SIYSIL on the same date. `normalize_action_type` matched
the substring "bonus" and misclassified both as canonical `BONUS`
(common-equity bonus), which fed `AdjustmentFactorBuilder` two
identical-looking rows.

Investigating that surfaced a much bigger, pre-existing bug:
`old_value` for every BONUS/SPLIT event has been sourced from the
`FACE_VALUE` column, not the actual ratio in the action text (e.g. "Bonus
1:1" with face value 10 and another "Bonus 1:1" with face value 5 were
producing *different* factors for the *same ratio*). This means every
adjustment factor the pipeline has ever computed for a real bonus/split
was likely wrong. Fixed in commit `c13eca1`:
- `_ACTION_TYPE_MAP` now checks "scheme of arrangement" before "bonus",
  so NCRPS/preference-share schemes classify as MERGER, not BONUS.
- `FieldNormalizer.extract_bonus_adjustment_factor` /
  `extract_split_adjustment_factor` parse the real ratio out of
  `ACTION_TYPE_RAW` ("Bonus X:Y", "From Rs A/- ... To Rs B/-") and
  `old_value` now uses these for BONUS/SPLIT/REVERSE_SPLIT instead of
  face value.
- `AdjustmentFactorBuilder` now merges multiple genuine same-day events
  for a security into one output row instead of one row per event, so a
  legitimate multi-event day can't crash the duplicate-key check either.
- 14 new tests added; full suite (442 tests) and `ruff check` both pass.
  Verified via a local `--dry-run` full pipeline run (extract through
  load) — `adjust` now succeeds and computed factors match hand-checked
  ratios (e.g. "Bonus 1:1" → 0.5, "10 → 2" face-value split → 0.2).

**Not yet done:** re-running the full historical pipeline / re-importing
Dolt so previously-published `fact_adjustment_factor` rows (computed with
the old face-value bug) get corrected — existing Dolt history and any
already-shipped release still has the wrong factors until a fresh
`load` runs. Next session should confirm this looks right in Dolt and
consider whether any published release needs a correction note.

## (2026-09-05) Website migrated Pages → Workers; nightly.yml and release.yml removed

The public site (`website/landing-page` → `website/public`) now deploys as a
Cloudflare Worker (`src/index.js`, `wrangler.jsonc`, `package.json` +
eslint/vitest/playwright), matching the structure of the `quietrollout`
project. Domain mapping and GitHub git-integration (Cloudflare Workers
Builds) are now configured in the dashboard — pushes to `main` build and
deploy the Worker automatically (build command must run
`hugo --source website/blog --destination ../public/blog --minify` before
`wrangler deploy`; confirm this is actually set in the Worker's Build
settings). `functions/api/{contact,razorpay-webhook}.js` and
`website/*/functions/_middleware.js` (Pages Functions) were merged into
`src/index.js`'s `fetch` handler.

Same session, at the user's explicit request (not an implication of the
website migration — these workflows have nothing to do with the website):
**`nightly.yml` and `release.yml` were deleted.** This means:
- The Mon–Fri NSE data refresh into Dolt no longer runs automatically.
- Tag-triggered releases (export, R2 upload, GitHub Release, website
  release-notes injection) no longer run automatically.

Both are now fully manual — see `docs/deploy.md` §6/§7 and
`docs/runbook.md` for the by-hand replacement commands. `ci.yml` (lint,
pytest, Hugo build-check) was kept as-is; it was never related to
deployment. If nightly/release automation is wanted back, restore from git
history: `git log -- .github/workflows/nightly.yml .github/workflows/release.yml`.
