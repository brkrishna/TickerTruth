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
- `website/` — Cloudflare Pages landing page and docs mirror
- `.github/workflows/` — ci.yml, nightly.yml, release.yml
- First release tagged: `v2026.06.01`

## Open items
- `tests/` directory exists but contains no test files yet — test suite is the highest-priority gap.
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

## Next suggested task
Write the initial test suite. Priority order:
1. `tests/test_normalize_*.py` — normalizer pure functions are the easiest entry point.
2. `tests/test_adjustments_factors.py` — parametrized ratio variants.
3. `tests/test_lineage_*.py` — rename, suspension/relisting, merger cases.
4. `tests/test_extract_*.py` — mocked network, consolidation idempotency.

## (2026-08-02) Data/release catch-up — findings and open bugs

Pushed release `v2026.08.02` (security master only — see
`releases/monthly/v2026.08.02.md` for full disclosure). While doing this,
found several real problems that need follow-up:

- **`fetch_nse_corporate_actions()` is broken** (`pipelines/extract/extractor.py`):
  fails against all three fallback sources — NSE JSON API
  (timeout/403/empty-body), Playwright (`ERR_HTTP2_PROTOCOL_ERROR`), and no
  stale cache to fall back to. Confirmed failing both locally and in GitHub
  Actions CI as of 2026-08-02. Because `run.py` treats extractor failures as
  non-fatal, `nightly.yml` has been reporting "success" every weekday while
  silently ingesting **zero corporate actions** for some unknown period —
  check how far back this goes. This is the highest-priority bug: corp
  actions/lineage/adjustment-factor data has likely been stale/empty in Dolt
  for a while. Needs real investigation (has NSE changed anti-bot measures?
  cookie handshake is failing with 403 on the homepage itself).
- **`nightly.yml` never persists Dolt state.** It does `dolt init` fresh
  every run (in the ephemeral CI runner) and never pushes/uploads it — so
  daily "refreshes" were being discarded, not accumulated. Added a
  `workflow_dispatch`-only artifact upload of `dolt/.dolt` + `data/curated`
  as a stopgap (see `.github/workflows/nightly.yml`), but the real fix needs
  a persistent Dolt remote (e.g. DoltHub) or committing Dolt state somewhere
  durable. This also means `release.yml` (export/manifest/release-notes/
  website) has been failing since 2026-06-02 — it needs `data/curated` from
  a prior `load` step but runs on a fresh checkout with no way to get it.
- **Bhavcopy is 814+ days stale** (last successful fetch: 2024-05-10).
  `fact_equity_eod` has never been populated via the pipeline.
- Local Dolt repo's pre-2026-08-02 commit history (May 31–June 2) was lost
  during this session (accidental `rm -rf dolt/.dolt` before confirming) —
  low impact since it only held dimension-table snapshots, no unique fact
  data, and was never pushed to a remote. Local Dolt now starts fresh from
  `v2026.08.02`.
- No git tags currently exist in this repo (`git tag -l` is empty) despite
  `release.yml` being tag-triggered — releases have apparently always been
  done via direct commits to `main`, not tag pushes.

Suggested priority: fix `fetch_nse_corporate_actions()` first (core product
value), then decide on a real Dolt persistence strategy for `nightly.yml`
before the next monthly release.
