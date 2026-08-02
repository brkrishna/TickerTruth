# Extract module

## Purpose
Downloads and archives untouched source data from NSE. This is the ingestion layer
of the ETL pipeline — it fetches raw data and writes it to `data/raw/` and
`data/staging/` without any normalization or transformation.

## Scope
- NSE equity master (symbol list) via `nsearchives.nseindia.com` archives mirror.
- NSE daily bhavcopy (EOD prices) zip files.
- NSE corporate actions via the NSE JSON API (with Playwright fallback for bot challenges).
- Consolidation of daily raw files into staging parquet.

## Files
- `extractor.py` — `RawDataExtractor` class implementing all four fetch steps.
- `sources.yaml` — URL configuration and source metadata for each data source.

## Source access notes
- NSE equity master: primary source is `nsearchives.nseindia.com/content/equities/EQUITY_L.csv`
  (no Akamai bot challenge). The `www.nseindia.com` API requires a session cookie.
- Corporate actions API (`nseindia.com/api/corporates-corporateActions`) requires a valid
  NSE session cookie. Playwright is used as a fallback to solve the bot challenge.
- EQUITY_L.csv lists only active EQ-series equities (~2,365 rows as of 2026).
  `STATUS` column is absent and synthesized to "ACTIVE" after load.
- Corporate actions API returns at most ~30 days per call; longer ranges are chunked.
- **(2026-08-02) `www.nseindia.com` is currently hard-blocked at Akamai's edge**
  (HTTP 403 "Access Denied", confirmed via `curl`/`requests` from both this
  sandbox and GitHub Actions CI — not a header/TLS-fingerprint issue, and not
  something `extractor.py` can retry its way past). This breaks the cookie
  handshake, the corporate actions JSON API, and the Playwright fallback (same
  domain, same edge). `RawDataExtractor` now detects the 403 on the homepage
  handshake and skips Playwright immediately rather than burning 30-60s on a
  fallback that's guaranteed to fail the same way, and logs at ERROR (not
  WARNING) so this doesn't go unnoticed the way it did for ~2 months in
  `nightly.yml`. Real fix requires an infrastructure change (different egress
  IP/proxy, or a licensed NSE data vendor) — out of scope for this module.
  `nsearchives.nseindia.com` (equity master) and `archives.nseindia.com`
  (bhavcopy) are NOT affected by this block.

## Output locations
- `data/raw/` — raw untouched files, one subdirectory per source and date.
- `data/staging/` — consolidated parquet files merged from daily raw files.

## Rules
- This module performs I/O only. No normalization, type casting, or business logic here.
- Never raise on a missing optional field; log a warning and retain the row.
- All network calls must include browser-like headers (NSE rejects bare requests).
- Do not delete raw files after consolidation; they are the immutable audit trail.
- Respect NSE rate limits: add delays between API requests.

## Testing rules
- Tests live in `tests/test_extract_*.py`.
- Network calls must be mocked; no live NSE requests in tests.
- Test that `consolidate_to_staging()` is idempotent (re-run does not duplicate rows).

## Done criteria
- `ruff check pipelines/extract/` passes.
- `pytest tests/test_extract_*.py -q` passes with no warnings.
- No normalization logic inside this module.
