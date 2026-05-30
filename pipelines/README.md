# ETL Pipeline Orchestration

This directory contains the modular ETL pipeline for the India Symbol History & Corporate Actions Truth Layer project.

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Scheduled ETL Orchestrator (Daily @ 6:00 AM IST)                 │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌─ pipelines/extract/ ───────────────────────────────────────────┐
│ Download untouched source files from NSE, NSDL, BSE             │
│ Inputs: NSE APIs, NSDL portal, BSE feeds                         │
│ Outputs: data/raw/ (immutable archive)                           │
│ ~30 minutes                                                      │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ pipelines/normalize/ ─────────────────────────────────────────┐
│ Parse, validate, deduplicate raw files                           │
│ Normalize formats, types, field names                            │
│ Quality checks and cross-source reconciliation                   │
│ Outputs: data/staging/ (Parquet + quality logs)                 │
│ ~15 minutes                                                      │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ pipelines/lineage/ ───────────────────────────────────────────┐
│ Build symbol chains, resolve entity identity                     │
│ Reconcile NSE/BSE cross-exchange listings                        │
│ Construct dim_security_master, dim_symbol_alias                 │
│ Outputs: data/curated/ (dimension & lineage events)             │
│ ~10 minutes                                                      │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ pipelines/adjustments/ ───────────────────────────────────────┐
│ Compute split, dividend, bonus adjustment factors               │
│ Build cumulative adjustment timeline per security               │
│ Validate price series normalization assumptions                 │
│ Outputs: data/curated/ (fact_adjustment_factor)                │
│ ~5 minutes                                                       │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ pipelines/publish/ ───────────────────────────────────────────┐
│ Import curated data into Dolt repository                         │
│ Generate free and paid tier sample exports                       │
│ Upload to CDN, create release tags and documentation             │
│ Outputs: Dolt commits + data/samples/                           │
│ ~30 minutes (includes validation, uploads)                       │
└────────────────────────────────────────────────────────────────┘
                              ↓
                    ✅ Daily Data Release
```

## Directory Structure

```
pipelines/
├── README.md                  # This file; pipeline overview
├── extract/                   # Phase 1: Download raw data
│   ├── __init__.py
│   └── README.md
├── normalize/                 # Phase 2: Parse & standardize
│   ├── __init__.py
│   └── README.md
├── lineage/                   # Phase 3: Resolve symbol chains
│   ├── __init__.py
│   └── README.md
├── adjustments/               # Phase 4: Compute price adjustments
│   ├── __init__.py
│   └── README.md
└── publish/                   # Phase 5: Import & distribute
    ├── __init__.py
    └── README.md
```

## Pipeline Responsibilities

### Phase 1: Extract
**Location**: `pipelines/extract/`

- Download from NSE, NSDL, BSE APIs and web portals
- Verify integrity (checksums, file size)
- Store immutably in `data/raw/` with metadata audit log
- Handle HTTP errors, retries, rate limiting

**Typical Execution**: ~30 minutes
**Output**: Raw CSV/TXT files, download log, checksums

---

### Phase 2: Normalize
**Location**: `pipelines/normalize/`

- Parse raw files (handle encoding, format variations)
- Standardize field names, data types, date formats
- Deduplicate records, validate cardinality
- Cross-source reconciliation (ISIN matches, orphan detection)
- Generate quality reports and error logs

**Typical Execution**: ~15 minutes
**Output**: Parquet staging files, quality logs, diagnostic CSVs

---

### Phase 3: Lineage
**Location**: `pipelines/lineage/`

- Build symbol lineage chains (ticker rename history)
- Resolve entity identity (company deduplication)
- Reconcile multi-exchange listings (NSE + BSE)
- Construct security master with surrogate keys
- Detect and flag conflicts (manual review items)

**Typical Execution**: ~10 minutes
**Output**: Curated dimension tables (exchange, issuer, security, alias)

---

### Phase 4: Adjustments
**Location**: `pipelines/adjustments/`

- Parse corporate action events (splits, dividends, bonuses, rights, mergers)
- Compute cumulative adjustment factors per security
- Build price normalization factors for backtesting
- Validate against historical price movements
- Flag unusual or conflicting actions

**Typical Execution**: ~5 minutes
**Output**: Curated fact tables (corporate action events, adjustment factors)

---

### Phase 5: Publish
**Location**: `pipelines/publish/`

- Import curated tables into Dolt repository
- Validate all constraints (FK, UNIQUE, NOT NULL)
- Generate free and paid tier sample exports
- Upload to CDN with checksums and metadata
- Create release tags, version documentation

**Typical Execution**: ~30 minutes (including validation, uploads)
**Output**: Dolt commits, release tags, sample exports, manifests

---

## Running the Pipeline

### Full Pipeline (All Phases)
```bash
python -m pipelines.extract
python -m pipelines.normalize
python -m pipelines.lineage
python -m pipelines.adjustments
python -m pipelines.publish
```

### Individual Phase
```bash
# Run just extract phase
python -m pipelines.extract --config config.yaml

# Run with dry-run (no writes)
python -m pipelines.normalize --dry-run
```

### Scheduled Execution (via cron/orchestrator)
```bash
# crontab entry (daily @ 6:00 AM IST)
0 6 * * * cd /path/to/ICASHTL && python -m pipelines.extract && python -m pipelines.normalize && python -m pipelines.lineage && python -m pipelines.adjustments && python -m pipelines.publish
```

---

## Configuration & Dependencies

Each phase has its own:
- `config.yaml`: Phase-specific settings (URLs, thresholds, schedules)
- `requirements.txt`: Python dependencies (install via `pip install -r pipelines/{phase}/requirements.txt`)
- `tests/`: Unit and integration tests

### Install All Dependencies
```bash
pip install -r pipelines/extract/requirements.txt
pip install -r pipelines/normalize/requirements.txt
pip install -r pipelines/lineage/requirements.txt
pip install -r pipelines/adjustments/requirements.txt
pip install -r pipelines/publish/requirements.txt
```

---

## Monitoring & Alerting

Each phase logs to:
- `data/raw/metadata/download_log.csv` (extract phase)
- `data/staging/{phase}_*.log` (all phases)
- `data/staging/reconciliation_report_{YYYYMMDD}.md` (summary report)

Monitor for:
- Phase failures (non-zero exit code)
- Data quality drops (quality_score < 0.80)
- Import constraint violations (Dolt import fails)
- Missing expected records (row count anomalies)

**Alert on**: Any phase failure → halt pipeline, notify on-call engineer

---

## Error Handling & Recovery

### Extract Phase Fails
- Most sources have daily retries built-in
- Check network connectivity, NSE API availability
- Inspect download logs for specific errors
- May proceed to next day (missing data for one day acceptable)

### Normalize Phase Fails
- Check raw file format changes (NSE sometimes updates column order)
- Review schema_definitions.yaml for format mismatches
- Manually inspect first few rows: `head -20 data/raw/nse/eod/*.csv`
- Fix parser; re-run normalize phase

### Lineage Phase Fails
- Check for orphan symbols (no matching ISIN, issuer)
- Review lineage_conflicts.csv for ambiguous mappings
- Resolve conflicts manually in config files
- Re-run lineage phase

### Adjustments Phase Fails
- Check for unusual corporate action dates (future dates, data entry errors)
- Review overlapping actions (split + dividend same day)
- Verify price data availability for ex-dates
- Inspect adjustment_conflicts.csv

### Publish Phase Fails
- Dolt FK constraints: check orphan foreign keys (missing issuer_id, exchange_id)
- Revert Dolt to previous commit: `dolt reset --hard HEAD~1`
- Fix data in normalize/lineage phases; re-run from start
- CDN upload fails: retry manually or check S3 permissions

---

## Performance Benchmarks

| Phase | Expected Time | Input Size | Output Size |
|-------|---------------|-----------|------------|
| Extract | ~30 min | N/A | ~50-100 MB |
| Normalize | ~15 min | 50-100 MB | ~20-30 MB (Parquet) |
| Lineage | ~10 min | 20-30 MB | ~10-15 MB (curated) |
| Adjustments | ~5 min | 20-30 MB | ~5-10 MB (curated) |
| Publish | ~30 min | 35-50 MB | ~10 MB (samples) + Dolt import |
| **Total** | **~90 min** | — | **~100-150 MB** |

---

## Data Lineage Tracking

Every record in the final dataset includes:
- `created_at`: When record was created (Dolt timestamp)
- `updated_at`: When record was last modified (Dolt timestamp)
- `confidence_score`: Data quality indicator (0.0–1.0)
- `source`: Which source system provided the data (NSE, NSDL, BSE, etc.)

Access via Dolt version control:
```bash
dolt log --oneline
dolt show <commit-hash>
dolt diff <commit1> <commit2> dim_security_master
```

---

## Development Guidelines

### Adding a New Data Source
1. Document in `pipelines/extract/source_registry.yaml`
2. Add parsing logic to `pipelines/normalize/transformers/`
3. Add validation rules in `pipelines/normalize/schema_definitions.yaml`
4. Add tests in `pipelines/normalize/tests/`
5. Integrate into lineage resolution if applicable

### Modifying Adjustment Logic
1. Update rules in `pipelines/adjustments/config.yaml`
2. Add special cases in `pipelines/adjustments/special_cases/`
3. Add unit tests in `pipelines/adjustments/tests/`
4. Validate price normalization in `tests/integration/test_price_normalization.py`

### Changing Sample Tier Definitions
1. Update `pipelines/publish/config.yaml` (tier row counts, formats)
2. Update export queries in `pipelines/publish/queries/`
3. Update templates in `pipelines/publish/templates/`
4. Test manually: `python -m pipelines.publish --test-export public`

---

## Next Steps

See individual README files in each pipeline phase:
- [extract/README.md](extract/README.md)
- [normalize/README.md](normalize/README.md)
- [lineage/README.md](lineage/README.md)
- [adjustments/README.md](adjustments/README.md)
- [publish/README.md](publish/README.md)
