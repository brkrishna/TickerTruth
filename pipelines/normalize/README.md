# Normalize Pipeline

## Responsibility

Parse, clean, and standardize raw source files into normalized intermediate datasets. This layer applies schema validation, data type conversions, deduplication, and basic quality checks. Output is staged in Parquet format for downstream reconciliation.

## Inputs

- Raw files from `data/raw/{source}/*.{csv,txt,zip}`
- Schema definitions for each source (field names, types, date formats)

## Outputs

- **Primary**: Normalized Parquet files → `data/staging/{dataset}_{YYYYMMDD}.parquet`
- **Validation**: Quality reports → `data/staging/{dataset}_issues.log`
- **Diagnostics**: Orphan records → `data/staging/{dataset}_orphaned.csv`
- **Audit**: Reconciliation gaps → `data/staging/reconciliation_gaps_{YYYYMMDD}.csv`

## Key Transformations

### 1. Parsing & Decoding
- Detect file encoding (UTF-8, Latin-1) and convert to UTF-8
- Handle multi-format files (e.g., NSE sometimes releases TXT vs CSV)
- Parse dates in various formats (DD-MMM-YYYY, YYYY-MM-DD, etc.) → ISO 8601
- Normalize line endings (CRLF → LF)

### 2. Field Normalization
- Convert column names to snake_case (e.g., `DATE_OF_LISTING` → `date_of_listing`)
- Trim leading/trailing whitespace
- Normalize numeric strings to typed DECIMAL (avoid float precision loss)
- Parse boolean strings (Y/N, True/False, 1/0) → BOOLEAN

### 3. Deduplication & Validation
- Detect and log duplicate rows (same key across entire dataset)
- Flag rows with critical missing fields (e.g., NULL symbol, NULL date)
- Validate field types & ranges (e.g., price >0, volume ≥0)
- Check date sequences (announcement ≤ ex_date ≤ record ≤ payment)

### 4. Cross-Source Reconciliation (Lightweight)
- Match ISIN to NSE/BSE symbols; flag mismatches
- Detect orphaned corporate actions (action with no matching security)
- Compare security counts across sources (flag significant deltas)
- Log all mismatches for manual review

### 5. Quality Metrics
- Calculate field-level fill rates (% non-NULL for each column)
- Identify outliers (e.g., price changes >100%, volume >10x average)
- Compute data quality score per file (0.0–1.0)
- Flag files with quality score <0.8

## Data Sources Normalized

| Source | Key Transformations |
|--------|-------------------|
| NSE Master | Deduplicate symbols, parse listing dates, normalize sectors |
| NSE EOD | Parse OHLCV, convert to DECIMAL, flag gaps (holidays) |
| Corp Actions | Parse ratios (split 1:2 → 2.0), validate date order, extract amounts |
| Symbol Changes | Match old→new symbols, parse merger targets, extract effective dates |
| ISIN Master | Deduplicate ISINs, match NSE/BSE codes, validate ISIN format |
| BSE Master | Normalize BSE codes, match to NSE symbols (cross-exchange) |

## Expected Artifacts

```
pipelines/normalize/
├── __init__.py
├── README.md                          # This file
├── normalizer.py                      # Core normalization engine
├── schema_definitions.yaml            # Field specs for each source
├── transformers/
│   ├── nse_master_transformer.py
│   ├── nse_eod_transformer.py
│   ├── corporate_actions_transformer.py
│   ├── symbol_changes_transformer.py
│   ├── isin_transformer.py
│   └── bse_transformer.py
├── validators.py                      # Type, range, cardinality validation
├── deduplicator.py                    # Duplicate detection & logging
├── config.yaml                        # Normalization rules, thresholds
├── requirements.txt                   # Dependencies (pandas, pyarrow, etc.)
└── tests/
    ├── test_transformers.py
    ├── test_validators.py
    ├── fixtures/
    │   ├── raw_equity_l.csv
    │   ├── raw_nse_eod.csv
    │   └── expected_normalized.parquet
    └── integration/
        └── test_end_to_end_normalize.py
```

## Implementation Notes

- Use **Pandas** for parsing, **PyArrow** for Parquet output
- Stream large files (don't load entirely into memory)
- Implement configurable validation rules per source (schema_definitions.yaml)
- Log all errors with: `{row_number}, {error_type}, {field_name}, {value}, {message}`
- Output both Parquet (efficient) and CSV (human-readable) for quality logs
- Generate quality report: row counts, fill rates, outlier counts, quality score

## Quality Thresholds

| Metric | Pass | Warn | Fail |
|--------|------|------|------|
| Field fill rate | >95% | 80-95% | <80% |
| Duplicate rows | 0% | 0-1% | >1% |
| Type conversion errors | 0% | 0-2% | >2% |
| Date validation errors | 0% | 0-1% | >1% |
| Quality score | >0.90 | 0.75-0.90 | <0.75 |

**Action on Fail**: Stop pipeline; alert data engineer; do NOT proceed to lineage stage

## SLA & Monitoring

- **Completion Time**: <15 minutes for all sources combined
- **Quality Gate**: Minimum 0.85 quality score per source
- **Logging**: All errors written to `data/staging/{source}_issues.log`
- **Alerts**: Automatic notification if any source fails quality threshold

## Next Steps

Output from this pipeline → **lineage/** pipeline (symbol chain resolution & entity matching)

Or directly to **adjustments/** if no symbol changes detected
