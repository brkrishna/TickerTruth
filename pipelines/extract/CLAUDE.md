# Extract module

## Purpose
Downloads and archives untouched source data from NSE. This is the ingestion layer
of the ETL pipeline — it fetches raw data and writes it to `data/raw/` and
`data/staging/` without any normalization or transformation.

## Scope
- NSE equity master (symbol list) via `nsearchives.nseindia.com` archives mirror.
- NSE daily bhavcopy (EOD prices) zip files.
- NSE corporate actions via the NSE JSON API (with Playwright fallback for bot challenges).
- Consolidation of daily raw files into staging CSVs.

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
- **(2026-08-14) CORRECTION — the "Akamai hard block" diagnosed 2026-08-02 was
  wrong.** `www.nseindia.com/` does return HTTP 403 for the homepage on every
  network tested, but that response still sets a working Akamai anti-bot
  cookie (`AKA_A2`) — `requests.Session` stores cookies from a response
  regardless of status code, and that cookie alone is enough to authenticate
  `NSE_CORP_ACTIONS_API`. Verified live 2026-08-14: 525 real corporate-action
  rows fetched in one call despite the homepage 403. The actual root cause of
  `fetch_nse_corporate_actions()` returning zero rows for ~2 months was a
  **missing `brotli` package** — NSE's API responses are Brotli-compressed,
  and without `brotli`/`brotlicffi` installed, `requests` silently receives
  undecoded bytes and `.json()` raises `JSONDecodeError`, which looked
  identical to a network/auth failure. Fixed by pinning `brotli==1.2.0` in
  `requirements.txt`. `_get_session()` and `fetch_nse_corporate_actions()` no
  longer treat a homepage 403 as fatal or use it to skip the Playwright
  fallback — see `tasks.md` INFRA-2 for the full writeup.
- **(2026-08-14) Bhavcopy URL/format migration — FIXED.** NSE retired the
  old `archives.nseindia.com/content/historical/EQUITIES/...` bhavcopy URL
  for current dates (still works for old archive dates) in favor of a new
  "UDiFF" format at `nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip`,
  with different column names (`TckrSymb`, `ClsPric`, etc.).
  `fetch_bhavcopy()` now tries the new URL first and falls back to the
  legacy one on 404; `_normalize_bhavcopy_columns()` maps both formats to
  the same canonical columns. See `tasks.md` INFRA-2 and
  `tests/test_extract_bhavcopy.py`.

## Output locations
- `data/raw/` — raw untouched files, one subdirectory per source and date.
- `data/staging/` — consolidated CSV files merged from daily raw files
  (DOC-1, `todo.md`: this doc previously said "parquet" — code has always
  written CSV throughout `data/raw/`, `data/staging/`, and `data/curated/`;
  corrected 2026-08-14. A Parquet migration is tracked separately as
  `todo.md`'s IO-1, not done).

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
