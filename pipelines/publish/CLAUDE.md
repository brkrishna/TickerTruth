# Publish module

## Purpose
Exports curated datasets into Dolt, generates subscriber-facing sample bundles,
packages paid-tier release artifacts, manages buyer access, and prepares
data warehouse migration exports.

## Scope
- Import curated parquet files from `data/curated/` into the Dolt repository.
- Validate data quality post-import (row counts, nulls, factor range checks).
- Generate public sample files (free tier) and paid-tier release bundles.
- Build and write `data/samples/metadata/` manifests for each release.
- Manage buyer records and generate signed Cloudflare R2 URLs for delivery.
- Generate cloud warehouse DDL and adapted sample queries (Snowflake, BigQuery, Databricks).
- Send release notification emails to subscribers.

## Files
- `dolt_importer.py` — loads curated parquet into Dolt, commits, and creates release tags.
- `data_validator.py` — post-import quality checks (counts, nulls, factor ranges, date ordering).
- `sample_generator.py` — creates free and paid-tier sample CSV/Parquet files.
- `packager.py` — bundles sample files into tier archives and uploads to R2.
- `manifest_builder.py` — writes `sample_manifest_{YYYYMMDD}.md` with row counts and file hashes.
- `access_manager.py` — buyer registry (flat CSV), signed R2 URL generation, download audit log.
- `release_notifier.py` — email notifications to subscribers on new release.
- `warehouse_exporter.py` — generates DDL and sample queries for cloud warehouse migration.
- `config.yaml` — tier definitions, sample sizes, R2 bucket config, email settings.

## Output locations
- `data/samples/public/` — free-tier samples.
- `data/samples/paid_tier_1/` — Explorer/Starter tier bundles.
- `data/samples/paid_tier_2/` — Professional tier bundles.
- `data/samples/metadata/` — manifests per release date.
- `data/warehouse/{target}/` — warehouse migration DDL and queries.
- `data/buyers/` — buyer registry CSVs (never committed to git).
- `releases/monthly/` — versioned release notes archive.

## Tiers
| Tier | Bundle contents |
|---|---|
| Free | Top-100 large-cap active securities, 30-day EOD snapshot, latest 100 corporate actions |
| Tier 1 (Explorer/Starter) | 1000+ securities, 1-year EOD history, 3-year corporate actions (Parquet) |
| Tier 2 (Professional) | Full security master, complete price history, all corporate actions (Parquet) |

## Rules
- Halt pipeline on import failure; do not proceed to sample generation with partial data.
- Signed R2 URLs expire in 7 days by default; log all generated URLs with buyer ID.
- Buyer state lives in flat CSV files (no database for MVP) — treat as sensitive, never commit.
- Warehouse export logic must remain decoupled from delivery channel.
- All release artifacts must include a checksum in the manifest.

## Done criteria
- `ruff check pipelines/publish/` passes.
- `pytest tests/test_publish_*.py -q` passes with no warnings.
- Dolt import is idempotent (re-running does not duplicate rows).
- Every release artifact is logged in the manifest with row count and hash.
