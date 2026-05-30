# Data Pipeline Architecture

This directory contains the India Symbol History & Corporate Actions Truth Layer data pipeline, organized in four distinct layers from raw ingestion to public distribution.

## Directory Structure & Purpose

```
data/
├── raw/          # Untouched source downloads (write-once, immutable)
├── staging/      # Normalized intermediate outputs (transformation working area)
├── curated/      # Final table-ready files (source of truth for Dolt import)
├── samples/      # Public sample exports (redistributable, anonymized if needed)
└── README.md     # This file
```

---

## 1. `raw/` — Source Downloads (Immutable Layer)

**Purpose:** Archive untouched, byte-for-byte copies of all external source files. No transformations applied.

**Access Pattern:** Write-once, read-many. Files should never be modified after initial download.

**Subdirectory Structure:**

```
raw/
├── nse/
│   ├── master/              # NSE equity master snapshots
│   │   ├── EQUITY_L_20260530.csv
│   │   ├── EQUITY_L_20260529.csv
│   │   └── ...
│   ├── eod/                 # NSE end-of-day OHLCV
│   │   ├── 2026/
│   │   │   ├── EQUITY_20260530.csv
│   │   │   ├── INFY_30MAY2026.csv
│   │   │   └── ...
│   │   └── 2025/
│   ├── corporate_actions/   # Corporate action announcements
│   │   ├── ca_202605.csv
│   │   ├── ca_202604.csv
│   │   └── ...
│   └── symbol_changes/      # Ticker renames, delistings, etc.
│       ├── symbol_changes_2026.txt
│       ├── delistings_2026.txt
│       └── ...
├── nsdl/
│   ├── isin_master_20260515.csv
│   ├── isin_master_20260215.csv
│   └── ...
├── bse/
│   ├── bse_equities_20260530.csv
│   ├── bse_equities_20260529.csv
│   └── ...
└── metadata/
    ├── download_log.csv     # Audit log: source URL, timestamp, hash, file size
    └── source_checksums.txt # SHA256 checksums for integrity verification
```

### Key Characteristics

**Storage & Retention:**
- **Format**: Original source format (CSV, TXT, ZIP)
- **Naming Convention**: `{DATASET}_{YYYYMMDD}.{ext}` or `{DATASET}_{DDMMMYYYY}.{ext}`
- **Retention**: Perpetual (required for audit trail and reproducibility)
- **Size Estimate**: ~50-100 GB after 2 years of daily NSE EOD ingestion

**Quality & Validation:**
- Files stored with download timestamp and source URL in metadata log
- SHA256 checksum computed and stored for integrity verification
- No decompression, decoding, or transformation applied
- Files archived in versioned Git LFS if version control needed

**Access Rules:**
- ✅ Read-only: Historical analysis, audit trails
- ✅ Append-only: Log new downloads with metadata
- ❌ Delete: Never delete raw files (immutable archive)
- ❌ Modify: Never edit raw files; create new version instead

### Processing Notes
- If source file is ZIP archive, extract and store individual CSVs with archive metadata
- For multi-line CSVs (e.g., symbol with embedded newlines), store as-is; handle parsing in staging
- Encoding issues: Store original bytes; document encoding in metadata (UTF-8, Latin-1, etc.)

---

## 2. `staging/` — Normalized Intermediate Outputs

**Purpose:** Transform raw files into clean, standardized intermediate datasets. This is the working area for data engineers to debug and iterate.

**Access Pattern:** Read-write during ingestion pipeline. Safe to delete and regenerate (non-authoritative).

**Subdirectory Structure:**

```
staging/
├── nse_master/              # Parsed & deduplicated security master
│   ├── nse_master_20260530.parquet
│   ├── nse_master_20260530.schema.json
│   └── nse_master_20260530_issues.log  # Parsing errors, duplicates detected
├── nse_eod/                 # Normalized OHLCV time series
│   ├── nse_eod_20260530.parquet
│   ├── nse_eod_20260530_gaps.csv      # Trading halts, missing dates
│   └── nse_eod_validation.log
├── corporate_actions/       # Parsed corporate action events
│   ├── corp_actions_202605.parquet
│   ├── corp_actions_202605_orphaned.csv  # Actions with no matching security
│   └── corp_actions_validation.log
├── symbol_changes/          # Parsed symbol lineage events
│   ├── symbol_changes_2026.parquet
│   └── symbol_changes_2026_validation.log
├── isin_mapping/            # Parsed ISIN-symbol cross-reference
│   ├── isin_mapping_20260515.parquet
│   └── isin_mapping_gaps.csv  # Securities with missing ISIN
├── bse_master/              # BSE ticker reference (optional, phase 2)
│   ├── bse_master_20260530.parquet
│   └── bse_master_validation.log
└── audit_logs/
    ├── ingestion_errors_202605.json   # All parsing errors with line numbers
    ├── data_quality_report_202605.md  # Quality metrics summary
    └── reconciliation_gaps_202605.csv # Mismatches between sources
```

### Key Characteristics

**Format & Encoding:**
- **Primary Format**: Parquet (compressed columnar, schema validation, cross-platform)
- **Backup Format**: CSV for human inspection and debugging
- **Encoding**: UTF-8 normalized (with escaping for special characters)
- **Schema**: Explicit JSON schema file for each Parquet dataset

**Transformations Applied:**

1. **Parsing & Decoding**
   - Detect and handle multi-format files (e.g., NSE sometimes releases TXT vs CSV)
   - Normalize field names to snake_case (e.g., `DATE_OF_LISTING` → `date_of_listing`)
   - Parse date strings to ISO 8601 format (YYYY-MM-DD)
   - Parse numeric strings to typed decimals (avoid floating-point precision loss)

2. **Data Quality Fixes**
   - Trim leading/trailing whitespace from all text fields
   - Normalize ticker symbols to UPPERCASE
   - Remove duplicate rows (log duplicates to `*_duplicates.csv`)
   - Flag and isolate rows with missing critical fields

3. **Reconciliation**
   - Cross-reference ISIN to NSE/BSE symbols; flag mismatches
   - Check for orphaned corporate actions (action_id with no matching security)
   - Validate date sequences (announcement_date ≤ ex_date ≤ record_date ≤ payment_date)

**Quality Logging:**
- Every file paired with `.log` or `_issues.csv` documenting errors encountered
- Log format: `{row_number},{error_type},{message},{value}`
- Examples: parsing errors, type mismatches, null/missing fields, orphan references

**Retention & Cleanup:**
- **Retention**: Keep 30 days rolling (regenerate during each daily pipeline run)
- **Cleanup**: Safe to delete; can be regenerated from raw/ by re-running ETL
- **Size Estimate**: ~5-10 GB per month (parquet compression ~10-15x smaller than raw CSV)

**Access Rules:**
- ✅ Read: For validation, debugging, manual inspection
- ✅ Write: For adding derived quality metrics, reconciliation results
- ✅ Delete: Safe to delete; data is not authoritative
- ❌ Direct production use: Do NOT load staging data into Dolt directly

---

## 3. `curated/` — Final Table-Ready Files (Source of Truth)

**Purpose:** Production-ready datasets that match Dolt schema exactly. Single source of truth before import into Dolt repository.

**Access Pattern:** Read-only output from ETL. Used as input to `dolt sql < curated/table.sql`.

**Subdirectory Structure:**

```
curated/
├── dim_exchange/
│   ├── dim_exchange_20260530.parquet
│   ├── dim_exchange_20260530.sql
│   └── dim_exchange_20260530_manifest.json  # Row count, checksums
├── dim_issuer/
│   ├── dim_issuer_20260530.parquet
│   ├── dim_issuer_20260530.sql
│   └── dim_issuer_manifest.json
├── dim_security_master/
│   ├── dim_security_master_20260530.parquet
│   ├── dim_security_master_20260530.sql
│   └── dim_security_master_manifest.json
├── dim_symbol_alias/
│   ├── dim_symbol_alias_20260530.parquet
│   ├── dim_symbol_alias_20260530.sql
│   └── dim_symbol_alias_manifest.json
├── dim_corporate_action_type/
│   ├── dim_corporate_action_type_20260530.parquet
│   ├── dim_corporate_action_type_20260530.sql
│   └── dim_corporate_action_type_manifest.json
├── fact_equity_eod/
│   ├── fact_equity_eod_20260530.parquet
│   ├── fact_equity_eod_20260530.sql
│   └── fact_equity_eod_manifest.json
├── fact_corporate_action_event/
│   ├── fact_corporate_action_event_20260530.parquet
│   ├── fact_corporate_action_event_20260530.sql
│   └── fact_corporate_action_event_manifest.json
├── fact_adjustment_factor/
│   ├── fact_adjustment_factor_20260530.parquet
│   ├── fact_adjustment_factor_20260530.sql
│   └── fact_adjustment_factor_manifest.json
├── fact_symbol_lineage_event/
│   ├── fact_symbol_lineage_event_20260530.parquet
│   ├── fact_symbol_lineage_event_20260530.sql
│   └── fact_symbol_lineage_event_manifest.json
├── fact_listing_status_history/
│   ├── fact_listing_status_history_20260530.parquet
│   ├── fact_listing_status_history_20260530.sql
│   └── fact_listing_status_history_manifest.json
└── metadata/
    ├── import_manifest_20260530.json    # Master manifest for entire import
    ├── schema_version.txt               # Dolt schema version imported
    └── import_log_20260530.txt          # Success/failure per table
```

### Key Characteristics

**Format & Schema Compliance:**
- **Format**: Parquet + SQL insert statements (dual format for validation)
- **Schema Match**: Every column, type, constraint matches Dolt schema exactly
- **Naming**: Filenames include timestamp (`_YYYYMMDD`) for traceability
- **Manifests**: Each table includes metadata (row count, data quality score, confidence_score distribution)

**Data Qualities Required:**

1. **Referential Integrity**
   - All foreign keys resolved to existing primary keys
   - No orphaned fact records pointing to non-existent dimensions
   - Validated in staging; flagged records excluded

2. **Type Safety**
   - All values match declared column types (INT, VARCHAR, DECIMAL, DATE, ENUM, BOOLEAN)
   - No unexpected NULL values in NOT NULL columns
   - ENUM values validated against allowed set

3. **Uniqueness & Cardinality**
   - UNIQUE constraints validated (e.g., no duplicate symbols in dim_security_master)
   - Surrogate key (id) uniqueness verified
   - Natural key uniqueness verified (e.g., (security_id, trading_date) in fact_equity_eod)

4. **Temporal Consistency**
   - Dates in correct order (announcement_date ≤ ex_date ≤ payment_date)
   - No future dates (except for known future events)
   - created_at ≤ updated_at ≤ CURRENT_TIMESTAMP

5. **Data Range Validation**
   - Price range checks: OHLC within ±50% of previous trading day (flag outliers)
   - Volume outliers: >500% change from average (flag; may be valid for splits)
   - Adjustment factors: >0 and typically <1.1 or >0.9 (outside range flagged)

**Confidence Scoring:**
- Each record includes `confidence_score` (0.0–1.0) indicating data quality
- Source determination: NSE official = 0.95+, parsed web = 0.75–0.95, estimated = <0.75
- Aggregated confidence reported in manifest

**Import Workflow:**
```bash
# After data pipeline completes:
cd dolt/
dolt sql < ../data/curated/dim_exchange_20260530.sql
dolt sql < ../data/curated/dim_issuer_20260530.sql
# ... import all curated tables ...
dolt add .
dolt commit -m "Daily ETL import: 2026-05-30"
```

**Retention:**
- Keep last 12 months (rolling archive)
- Older imports available in Dolt history (dolt log)
- Size estimate: ~5-20 MB per daily import (compressed)

---

## 4. `samples/` — Public Sample Exports (Redistributable)

**Purpose:** Curated public subsets for buyers, analysts, or open-source sharing. Non-sensitive demonstration data.

**Access Pattern:** Read-only exports from Dolt after import. Distributed to external parties.

**Subdirectory Structure:**

```
samples/
├── public/
│   ├── nse_active_securities_sample.csv
│   │   └── (Top 100 large-cap NSE equities: symbol, ISIN, sector, market cap)
│   ├── equity_eod_sample_20260530.csv
│   │   └── (Last 30 days OHLCV for top 10 equities)
│   ├── corporate_actions_sample_20260530.csv
│   │   └── (Last 100 corporate actions, anonymized company names if needed)
│   ├── adjustment_factors_reference.csv
│   │   └── (Sample cumulative adjustment factors for backtesting reference)
│   └── symbol_lineage_sample.csv
│       └── (Last 50 symbol changes, name updates, mergers)
├── paid_tier_1/
│   ├── extended_nse_master_20260530.csv
│   │   └── (1000+ equities with sector, market cap, listing date)
│   ├── equity_eod_1yr_20260530.parquet
│   │   └── (1 year OHLCV for top 100 equities)
│   ├── corporate_actions_3yr_20260530.parquet
│   │   └── (3 years of corporate actions, full detail)
│   └── nse_index_constituents.csv
├── paid_tier_2/
│   ├── full_security_master_20260530.parquet
│   │   └── (All NSE listed + delisted equities)
│   ├── equity_eod_full_history.parquet
│   │   └── (Complete price history from 2016+)
│   ├── corporate_actions_full_history.parquet
│   │   └── (All corporate actions with confidence scores)
│   └── adjustment_factors_full_history.parquet
├── metadata/
│   ├── sample_manifest_20260530.md
│   │   └── Description, record counts, date range for each export
│   ├── schema_documentation.md
│   │   └── Field definitions, data types, business rules
│   └── license_terms.txt
│       └── Usage rights, attribution requirements
└── exports_log.csv
    └── (Audit log: export date, recipient, tier, access timestamp)
```

### Key Characteristics

**Public Tier (Free/Open):**
- **Use Case**: Marketing, community engagement, educational content
- **Contents**: 
  - Top 100 large-cap stocks (leaders, visibility)
  - 30-day OHLCV snapshot (sufficient for demo analysis)
  - 50 recent corporate actions (recent activity showcase)
  - Symbol lineage examples (show data richness)
- **Size**: ~1-2 MB
- **Frequency**: Updated daily
- **Format**: CSV (human-readable, Excel-compatible)
- **Privacy**: No sensitive data; company names are public

**Paid Tier 1 (Mid-Market):**
- **Use Case**: Traders, analysts, fintech startups
- **Contents**:
  - 1000+ equities (broad market coverage)
  - 1 year of OHLCV history (backtesting capability)
  - 3 years of corporate actions (event analysis)
  - NSE index constituent lists (benchmark alignment)
- **Size**: ~20-50 MB (compressed)
- **Frequency**: Weekly refresh
- **Format**: Parquet (compact, schema-safe)
- **License**: Non-commercial or commercial (negotiable)

**Paid Tier 2 (Enterprise):**
- **Use Case**: Institutional investors, portfolio managers, compliance teams
- **Contents**:
  - All listed equities (complete coverage)
  - Full price history (2016+, ~2.5 TB potential)
  - Complete corporate action history (audit-ready)
  - Adjustment factors for all securities (research-grade)
- **Size**: 100+ GB (uncompressed Parquet)
- **Frequency**: Daily or streaming API
- **Format**: Parquet + Dolt repository access (version control)
- **License**: Commercial, with SLAs and support

**Export Metadata:**
- `sample_manifest_YYYYMMDD.md`: Record counts, date ranges, data quality metrics
- `schema_documentation.md`: Field definitions, business logic, calculations
- `license_terms.txt`: Usage rights, attribution, restrictions

**Quality Standards for Public Exports:**
- ✅ Only data with confidence_score ≥ 0.85 (high quality)
- ✅ All foreign key constraints validated
- ✅ No stale data (records >5 years old marked deprecated)
- ✅ Consistent encoding (UTF-8)

**Distribution & Versioning:**
- Samples uploaded to CDN or S3 bucket (with signed URLs)
- Version pinned by date (`equity_eod_sample_20260530.csv`)
- Checksums (MD5, SHA256) provided for integrity verification
- Change log maintained: `exports_log.csv` tracks all distributions

**Retention & Archival:**
- Keep last 12 months of sample exports
- Older versions available via API/archive if requested
- Size estimate: 50-100 MB per day (rolling storage)

---

## Data Pipeline Workflow

```
┌──────────────────────────────────────────────────────────────────┐
│ SCHEDULED ETL JOB (Daily @ 6:00 AM IST)                          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Phase 1: Ingest ────────────────────────────────────────────────┐
│ → Download from NSE, NSDL, BSE sources                            │
│ → Verify checksums (integrity check)                             │
│ → Store in raw/ with metadata & timestamps                       │
│ → Log to data/raw/metadata/download_log.csv                      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Phase 2: Transform ────────────────────────────────────────────┐
│ → Parse CSVs/TXTs from raw/                                      │
│ → Normalize field names, formats, encodings                      │
│ → Validate data types, ranges, cardinality                       │
│ → Log errors to staging/*_issues.log                            │
│ → Output normalized Parquets to staging/                         │
│ → Generate quality report                                        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Phase 3: Reconcile ────────────────────────────────────────────┐
│ → Cross-reference data across sources                            │
│ → Resolve foreign key relationships                              │
│ → Flag orphans, mismatches, confidence scores                    │
│ → Curate dimension & fact datasets per Dolt schema               │
│ → Output to curated/                                             │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Phase 4: Import ──────────────────────────────────────────────┐
│ → Load curated tables into Dolt                                  │
│ → Validate constraints (FK, UNIQUE, NOT NULL)                   │
│ → Commit to Dolt with message (e.g., "Daily ETL: 2026-05-30")  │
│ → Tag release (v2026.05.30)                                      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Phase 5: Export ──────────────────────────────────────────────┐
│ → Generate public samples from Dolt query results               │
│ → Create paid tier subsets                                       │
│ → Upload to CDN with checksums & metadata                        │
│ → Update exports_log.csv                                         │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    ✅ Pipeline Complete
```

---

## Storage Estimates & Capacity Planning

| Layer | Retention | Daily Delta | 1-Year Total |
|-------|-----------|------------|--------------|
| raw/ | Perpetual | ~50-100 MB | ~18-36 GB |
| staging/ | 30 days | ~20-30 MB | ~5-10 GB (rolling) |
| curated/ | 12 months | ~5-10 MB | ~1-3 GB |
| samples/ | 12 months | ~5-20 MB | ~2-7 GB |
| **Total** | — | — | **~26-56 GB** |

---

## Best Practices & Conventions

### Naming Conventions
- **Raw files**: `{DATASET}_{YYYYMMDD}.{ext}` (e.g., `EQUITY_L_20260530.csv`)
- **Parquet files**: `{table_name}_{YYYYMMDD}.parquet`
- **SQL inserts**: `{table_name}_{YYYYMMDD}.sql`
- **Logs**: `{operation}_{YYYYMMDD}.log` (e.g., `ingestion_errors_202605.log`)

### Error Handling
- All errors logged with: `{timestamp},{error_type},{source_file},{line_number},{message}`
- Critical errors: Stop pipeline; alert on-call engineer
- Non-critical errors: Log and continue; review in daily quality report
- Data quality threshold: >95% success rate for import to proceed

### Version Control
- `data/raw/` and `data/curated/` tracked in Git LFS (large files)
- `data/staging/` NOT tracked (regenerable; use .gitignore)
- Schema changes (dolt/schema.sql) trigger re-curated dataset generation
- Dolt commits include reference to curated dataset version

### Access & Permissions
- **raw/**: Read-only for all users (write via automated ETL only)
- **staging/**: Read-write for data engineers; scripts handle generation
- **curated/**: Read-only for all users (generated by ETL pipeline)
- **samples/**: Public-read; managed by release process

---

## Troubleshooting & Recovery

**Q: Raw file corrupted; need to re-download**
- Delete corrupt file from raw/
- Re-run download phase (will re-fetch from NSE)
- Checksum mismatch will be logged in metadata

**Q: Staging quality report shows 40% parsing errors**
- Review staging/*_issues.log for error patterns
- Check raw/ source format (may have changed)
- Adjust parser in ETL script; re-run staging phase
- Do NOT import to Dolt until resolved (error rate <5%)

**Q: Curated dataset has orphaned corporate actions**
- Cross-check ISIN/symbol mapping in isin_mapping staging file
- May indicate new security not yet in master data
- Add security to dim_security_master manually; reprocess staging
- Or mark action with confidence_score = 0.3 and skip import

**Q: Sample exports missing recent data**
- Verify Dolt import completed successfully (dolt log)
- Re-run export phase (Phase 5)
- Check permissions on samples/ directory
- Verify CDN upload succeeded

