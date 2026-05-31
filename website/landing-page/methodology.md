# Methodology

## Source-to-Schema Process

### Phase 1: Extraction
- Pull NSE equity master and historical symbol data
- Collect corporate action announcements from NSE websites
- Download ticker mapping and alias history from official sources
- Store raw unprocessed files in `data/raw/`

### Phase 2: Normalization
- Standardize field names and formats across all sources
- Map source identifiers to canonical security IDs
- Validate dates, amounts, and ratios for consistency
- Store cleaned data in `data/staging/`

### Phase 3: Enrichment
- Build symbol lineage graphs (rename chains, mergers, splits)
- Compute adjustment factors for price series normalization
- Tag data quality issues and provenance
- Generate curated fact and dimension tables in `data/curated/`

### Phase 4: Publishing
- Export public sample subset to CSV/Parquet
- Generate paid full release bundles
- Update versioned Dolt repository
- Upload artifacts to storage

---

## Normalization Philosophy

- **Trust over completeness** — mark uncertain data with confidence flags rather than excluding it
- **Provenance first** — log source and transformation for every record
- **Audit trail** — keep all versions in Dolt for regulatory and analytical review
- **Fail gracefully** — missing data is better than wrong data; log gaps explicitly

---

## Data Model

### Dimension Tables

| Table | Purpose |
|---|---|
| `dim_security_master` | Central security identifier hub; NSE symbol, ISIN, active status |
| `dim_issuer` | Company/issuer identity; sector and market cap category |
| `dim_exchange` | Exchange reference (NSE, BSE); enables multi-exchange support |
| `dim_symbol_alias` | All historical symbols for a security with effective date ranges |
| `dim_corporate_action_type` | Immutable lookup: SPLIT, DIVIDEND, BONUS, MERGER, DELISTING, etc. |

### Fact Tables

| Table | Purpose |
|---|---|
| `fact_equity_eod` | End-of-day OHLCV price snapshots |
| `fact_corporate_action_event` | Normalized corporate action records with confidence scores |
| `fact_adjustment_factor` | Pre-computed cumulative adjustment multipliers for backtesting |
| `fact_symbol_lineage_event` | Ticker and name change history (renames, mergers, delistings) |
| `fact_listing_status_history` | Active, suspended, delisted, relisted status over time |

### Key Design Principles

- **Surrogate keys** — decouple logical identity from business keys
- **Soft deletes via flags** — keep historical records for audit trails
- **Temporal tracking** — `created_at` / `updated_at` on all tables
- **Confidence scoring** — `confidence_score` on every event allows buyers to filter by data quality
- **Flexible fact granularity** — `old_value`/`new_value` design supports multiple action types without separate tables

---

## Data Sources

All data is sourced from official NSE public sources:

- **NSE Equity Master** — listed companies, ISIN, listing dates, status
- **NSE Corporate Actions Board** — dividends, splits, bonus, rights, mergers, delistings
- **NSE Bhavcopy** — daily EOD trade data for price validation
- **NSE Circulars** — name changes, suspensions, relisting notices

Data quality is classified into three confidence tiers:

| Confidence | Sources |
|---|---|
| High (≥ 0.95) | NSE EOD OHLCV, NSE Corporate Action Board, NSDL ISIN Registry |
| Medium (0.7–0.95) | NSE historical archives, parsed web content, BSE cross-references |
| Low (< 0.7) | Estimated adjustment factors, reconstructed lineage from sparse data |

Every record in the published dataset includes a `confidence_score` and `_source_file` field for full traceability.