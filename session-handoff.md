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

## Next suggested task
Write the initial test suite. Priority order:
1. `tests/test_normalize_*.py` — normalizer pure functions are the easiest entry point.
2. `tests/test_adjustments_factors.py` — parametrized ratio variants.
3. `tests/test_lineage_*.py` — rename, suspension/relisting, merger cases.
4. `tests/test_extract_*.py` — mocked network, consolidation idempotency.
