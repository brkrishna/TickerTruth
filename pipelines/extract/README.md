# Extract Pipeline

## Responsibility

Download and archive untouched source data from NSE, NSDL, BSE, and other external sources. This is the ingestion layer that retrieves data and stores it in `data/raw/` with full provenance tracking.

## Inputs

- Configuration: Source URLs, download schedules, credentials (if any)
- Scheduler: Daily trigger (e.g., 6:00 AM IST post-market close)

## Outputs

- **Primary**: Raw downloaded files → `data/raw/{source}/{dataset}_{YYYYMMDD}.{ext}`
- **Metadata**: Download audit log → `data/raw/metadata/download_log.csv`
- **Validation**: Checksums → `data/raw/metadata/source_checksums.txt`

## Data Sources Handled

| Source | Frequency | Format | Size |
|--------|-----------|--------|------|
| NSE Master (EQUITY_L) | Daily | CSV/TXT | ~500 KB |
| NSE EOD OHLCV | Daily | CSV | ~10-15 MB |
| NSE Corporate Actions | Real-time, batch daily | HTML, CSV | ~5-10 MB |
| NSE Symbol Changes | Real-time, batch daily | TXT, PDF | ~500 KB |
| NSDL ISIN Master | Quarterly | CSV | ~200 MB |
| BSE Master | Daily | CSV | ~3-5 MB |

## Key Tasks

1. **HTTP Download & Retry**
   - Download from source URLs with exponential backoff (max 3 retries)
   - Log HTTP status, response time, error messages
   - Handle authentication if required (e.g., API keys from environment vars)

2. **File Integrity Verification**
   - Compute SHA256 checksum of downloaded file
   - Compare against known checksums if available (maintain registry)
   - Flag file corruption or incomplete downloads

3. **Storage & Archival**
   - Create dated subdirectories (e.g., `raw/nse/eod/2026/`)
   - Store files with timestamp suffix (e.g., `EQUITY_L_20260530.csv`)
   - Maintain `.gitignore` for large files (use Git LFS if versioning needed)

4. **Metadata Logging**
   - Record: `source_url, local_path, download_timestamp, file_size, checksum, status`
   - Log all errors with timestamps and context
   - Alert on repeated failures (e.g., NSE API down for >1 hour)

5. **Error Handling**
   - **Non-fatal**: Network timeouts, intermittent 5xx errors → retry with backoff
   - **Fatal**: 404 (URL invalid), malformed responses → manual investigation + alert
   - Continue with next source; do not block entire pipeline

## Expected Artifacts

```
pipelines/extract/
├── __init__.py
├── README.md                          # This file
├── download_manager.py                # Core download orchestration
├── source_registry.yaml               # URL registry for all sources
├── config.yaml                        # Download schedules, retry policies
├── requirements.txt                   # Dependencies (requests, boto3, etc.)
└── tests/
    ├── test_download_manager.py
    ├── test_http_resilience.py
    └── fixtures/
        ├── sample_equity_l.csv
        └── sample_nse_eod.csv
```

## Implementation Notes

- Use `requests` library with session pooling for efficiency
- Implement circuit-breaker pattern for source URLs (skip if consistently failing)
- Log all downloads to CloudWatch or local file for audit trails
- Consider parallel downloads for independent sources (max 3 concurrent)
- Decompress ZIP files; store individual CSVs (do not nest archives)

## SLA & Monitoring

- **Success Rate**: ≥95% of sources downloaded daily
- **Latency**: Complete all downloads within 30 minutes of trigger
- **Failure Alert**: Automatic notification if any source fails >3 retries
- **Reconciliation**: Verify download_log.csv has expected record counts

## Next Steps

Output from this pipeline → **normalize/** pipeline (parsing & validation)

# NSE Raw Data Extraction Pipeline

## Overview

This pipeline fetches raw data from National Stock Exchange (NSE) sources and persists them to `data/raw/` with metadata and validation checks. It is the first stage of Phase 2 (Data Ingestion and Normalization).

## Purpose

- Automate retrieval of NSE symbols, corporate actions, circulars, and market data
- Persist raw files with date stamps for traceability
- Detect extraction failures and data quality issues early
- Provide staging area for normalization pipeline

## Inputs

Configured sources in `sources.yaml`:
1. **NSE Listed Companies** → Symbol master, ISIN, listing dates
2. **NSE Corporate Actions** → Dividends, splits, bonus, mergers, delistings
3. **NSE Circulars** → Name changes, suspensions, delisting events
4. **NSE Bhavcopy** → Daily EOD market data (validation use)

## Outputs

Raw data files saved to `data/raw/`:
- `nse_symbols_{YYYY-MM-DD}.csv`
- `nse_actions_{YYYY-MM-DD}.csv`
- `nse_circulars_{YYYY-MM-DD}.csv`
- `bhavcopy_{YYYY-MM-DD}.csv`
- `extraction_log_{YYYY-MM-DD}.json` (metadata)
- `quality_report_{YYYY-MM-DD}.json` (validation results)

## Installation & Dependencies

```bash
# Install required packages
pip install pandas requests beautifulsoup4 playwright pdfplumber lxml
```

# For Playwright (browser automation)
```bash
playwright install chromium
```

# For OCR (optional, for scanned PDFs)
```bash
pip install pytesseract
# Also install Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki
```
## Manual Extraction for MVP Testing

```bash
# Extract all configured sources
python pipelines/extract/extractor.py --all

# Extract specific sources

python pipelines/extract/extractor.py --source nse_symbols
python pipelines/extract/extractor.py --source nse_actions
python pipelines/extract/extractor.py --source nse_circulars

# Extract with custom date
python pipelines/extract/extractor.py --all --date 2026-05-15

# Dry run (no file writes)
python pipelines/extract/extractor.py --all --dry-run

# Extracting individual Sources
# NSE Symbol Master

```python -c "
from pipelines.extract.extractor import RawDataExtractor
extractor = RawDataExtractor()
symbols_df = extractor.fetch_nse_symbols()
print(f'Fetched {len(symbols_df)} symbols')
print(symbols_df.head())
"
# NSE Corporate Actions

python -c "
from pipelines.extract.extractor import RawDataExtractor
extractor = RawDataExtractor()
actions_df = extractor.fetch_nse_corporate_actions(days_back=7)
print(f'Fetched {len(actions_df)} actions from last 7 days')
print(actions_df.head())
"

# NSE Circulars

python -c "
from pipelines.extract.extractor import RawDataExtractor
extractor = RawDataExtractor()
circulars_df = extractor.fetch_nse_circulars(days_back=7)
print(f'Fetched {len(circulars_df)} circulars')
print(circulars_df.head())
"

# NSE Bhavcopy (EOD Data)

python -c "
from pipelines.extract.extractor import RawDataExtractor
extractor = RawDataExtractor()
bhavcopy_df = extractor.fetch_nse_bhavcopy(date='2026-05-29')
print(f'Fetched {len(bhavcopy_df)} securities for 2026-05-29')
print(bhavcopy_df.head())
"