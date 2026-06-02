# Publish Pipeline

## Responsibility

Export curated datasets into Dolt, generate public-facing samples, and prepare distribution artifacts for buyers at different service tiers. This layer handles data import validation, sample generation, CDN uploads, and release documentation.

## Inputs

- Curated datasets from `data/curated/` (all dimension & fact tables)
- Dolt repository at `dolt/` (for version control and incremental import)
- Release configuration (tier definitions, sample sizes, export schedules)

## Outputs

- **Dolt Repository**:
  - Updated Dolt database with imported tables
  - Dolt commit with message (e.g., "Daily ETL: 2026-05-30")
  - Release tag (e.g., `v2026.05.30`)
- **Public Samples** (Free Tier):
  - `data/samples/public/nse_active_securities_sample.csv` (top 100 large-cap)
  - `data/samples/public/equity_eod_sample_{YYYYMMDD}.csv` (30-day snapshot)
  - `data/samples/public/corporate_actions_sample_{YYYYMMDD}.csv` (latest 100 actions)
- **Paid Tier 1 Exports**:
  - `data/samples/paid_tier_1/extended_nse_master_{YYYYMMDD}.csv` (1000+ securities)
  - `data/samples/paid_tier_1/equity_eod_1yr_{YYYYMMDD}.parquet` (1-year history)
  - `data/samples/paid_tier_1/corporate_actions_3yr_{YYYYMMDD}.parquet` (3-year history)
- **Paid Tier 2 Exports**:
  - `data/samples/paid_tier_2/full_security_master_{YYYYMMDD}.parquet` (all securities)
  - `data/samples/paid_tier_2/equity_eod_full_history.parquet` (complete price history)
  - `data/samples/paid_tier_2/corporate_actions_full_history.parquet` (all events)
- **Metadata & Distribution**:
  - `data/samples/metadata/sample_manifest_{YYYYMMDD}.md` (descriptions, row counts)
  - `data/samples/exports_log.csv` (audit trail of all exports)
  - `releases/` archive (release notes, version history)

## Key Tasks

### 1. Dolt Import & Commit
- Load curated Parquet files into Dolt using `LOAD DATA INFILE` or SQL inserts
- Validate all constraints (FK, UNIQUE, NOT NULL) post-import
- Verify row counts match source files (no data loss)
- Commit with message: `"Daily ETL import: YYYY-MM-DD (X new securities, Y corporate actions)"`
- Tag release: `dolt tag create v{YYYYMMDD}`

### 2. Data Validation (Post-Import)
- Run data quality queries (e.g., `SELECT COUNT(*) FROM fact_equity_eod WHERE trading_date = CURDATE()`)
- Check for NULL values in critical columns
- Validate adjustment factors (should be >0 and reasonable range)
- Compare new row counts vs. previous day (flag anomalies)
- Alert on import failures (halt further processing)

### 3. Public Sample Generation (Free Tier)
- **nse_active_securities_sample.csv**: Query top 100 by market cap
  ```sql
  SELECT nse_symbol, isin, company_name, sector, market_cap_category
  FROM dim_security_master
  WHERE active_flag = TRUE
  ORDER BY market_cap_category DESC, issuer_name ASC
  LIMIT 100;
  ```
- **equity_eod_sample.csv**: Last 30 days OHLCV for top 10 stocks
  ```sql
  SELECT * FROM vw_adjusted_price_reference_sample
  WHERE trading_date >= CURDATE() - INTERVAL 30 DAY;
  ```
- **corporate_actions_sample.csv**: Latest 100 corporate actions
  ```sql
  SELECT * FROM vw_action_timeline_sample LIMIT 100;
  ```

### 4. Paid Tier 1 Export (Mid-Market)
- **extended_nse_master**: All 1000+ active & recently-delisted securities
- **equity_eod_1yr**: Last 12 months OHLCV for top 100 equities (Parquet for efficiency)
- **corporate_actions_3yr**: All actions in past 3 years (Parquet compressed)
- Format: Parquet (compact, cross-platform schema safety)

### 5. Paid Tier 2 Export (Enterprise)
- **full_security_master**: All securities ever listed (including delisted)
- **equity_eod_full_history**: Complete price history from 2016+ (potentially 100+ GB)
- **corporate_actions_full_history**: All events with confidence scores
- Format: Parquet or direct Dolt repository clone
- Size: Monitor storage; compress or archive as needed

### 6. Checksum & Integrity Verification
- Compute SHA256 checksum for each exported file
- Store checksums in manifest or separate file
- Buyers can verify download integrity
- Example: `sha256sum equity_eod_sample_20260530.csv > equity_eod_sample_20260530.sha256`

### 7. Metadata Documentation
- Generate `sample_manifest_{YYYYMMDD}.md`:
  - Row counts per file
  - Date range (e.g., "2026-04-30 to 2026-05-30")
  - Data quality metrics (e.g., "99.2% fill rate in OHLC fields")
  - Confidence score distribution
  - Sample query examples
- Generate `schema_documentation.md`: Field definitions, business logic, calculation notes
- Update `license_terms.txt` with usage rights per tier

### 8. CDN Upload & Distribution
- Upload public samples to public S3 bucket (anonymous read access)
- Upload paid tier samples to private S3 bucket (signed URLs for buyers)
- Generate signed URLs with expiration (e.g., 7 days)
- Send download links to buyers via email/API
- Log all downloads in `exports_log.csv` for compliance

### 9. Release Notes & Versioning
- Create release notes: `releases/v{YYYYMMDD}.md`
  - Summary: securities added/removed, corporate actions processed
  - Schema changes (if any)
  - Known issues or data quality flags
  - Breaking changes (if any)
- Update main `README.md` with latest release info

### 10. Cleanup & Archive
- Move old samples (>12 months) to cold storage archive
- Keep last 12 months online for easy access
- Maintain perpetual archive in S3 Glacier for compliance
- Log all archive actions in `exports_log.csv`

## Expected Artifacts

```
pipelines/publish/
├── __init__.py
├── README.md                          # This file
├── dolt_importer.py                   # Load curated data into Dolt
├── sample_generator.py                # Export queries for each tier
├── data_validator.py                  # Post-import validation
├── checksum_generator.py              # SHA256 computation
├── manifest_builder.py                # Metadata documentation
├── cdn_uploader.py                    # S3/CDN upload logic
├── release_notifier.py                # Generate release notes, email alerts
├── config.yaml                        # Sample definitions, tier configs
├── queries/
│   ├── public_samples.sql             # Public tier export queries
│   ├── tier1_exports.sql              # Tier 1 export queries
│   └── tier2_exports.sql              # Tier 2 (enterprise) export queries
├── templates/
│   ├── manifest_template.md           # Sample manifest boilerplate
│   ├── release_notes_template.md      # Release notes template
│   └── license_terms.md               # License text per tier
├── requirements.txt                   # Dependencies (boto3, pandas, etc.)
└── tests/
    ├── test_dolt_import.py
    ├── test_sample_generation.py
    ├── test_data_validation.py
    ├── fixtures/
    │   ├── sample_curated_data.parquet
    │   └── expected_exports.parquet
    └── integration/
        └── test_end_to_end_publish.py
```

## Dolt Import Workflow

```bash
#!/bin/bash
# publish_to_dolt.sh

cd /path/to/TickerTruth/dolt

# Check if tables already exist; back up if needed
dolt tables

# Import each curated table
for table in dim_exchange dim_issuer dim_security_master dim_symbol_alias dim_corporate_action_type; do
  echo "Importing $table..."
  dolt sql < ../data/curated/${table}/$(ls -t ../data/curated/${table}/*.sql | head -1)
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to import $table"
    exit 1
  fi
done

# Verify imports
dolt sql -q "SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES;"

# Commit
dolt add .
dolt commit -m "Daily ETL import: $(date +%Y-%m-%d)"

# Tag release
dolt tag create v$(date +%Y%m%d)

# Output success
echo "✅ Import complete. Run 'dolt log' to verify commits."
```

## Sample Query Examples

```sql
-- Public: Top 100 large-cap stocks
SELECT nse_symbol, company_name, sector FROM dim_security_master
WHERE active_flag = TRUE ORDER BY market_cap_category LIMIT 100;

-- Tier 1: 1-year price history
SELECT trading_date, nse_symbol, close_price, volume
FROM fact_equity_eod
WHERE trading_date >= CURDATE() - INTERVAL 365 DAY
AND security_id IN (SELECT security_id FROM dim_security_master 
                    WHERE active_flag = TRUE LIMIT 100);

-- Tier 2: Complete adjustment factor history
SELECT security_id, as_of_date, total_adjustment_factor
FROM fact_adjustment_factor
ORDER BY security_id, as_of_date;
```

## SLA & Monitoring

- **Import Latency**: <30 minutes post-ETL completion
- **Data Validation**: 100% of constraints must pass
- **Sample Generation**: <10 minutes for all tiers
- **CDN Upload**: <5 minutes (parallel upload for large files)
- **Export Availability**: Within 1 hour of pipeline completion

## Error Handling & Rollback

| Error | Action |
|-------|--------|
| FK constraint violation on import | Halt; investigate orphan data; fix in normalize pipeline |
| Row count mismatch vs. curated file | Halt; compare manually; investigate data loss |
| CDN upload failure | Retry 3x with backoff; alert team if all fail |
| Sample query returns 0 rows | Alert data engineer; investigate data availability |

**Rollback**: If critical errors detected, revert Dolt to previous commit (`dolt reset --hard <commit-hash>`) and investigate.

## Next Steps

Output complete → Distribution ready for buyers

Monitor alerts → Prepare for next daily pipeline run
