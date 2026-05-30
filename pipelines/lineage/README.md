# Lineage Pipeline

## Responsibility

Build and reconcile symbol lineage chains, entity identity graphs, and ticker-to-security mappings. This layer constructs the `dim_security_master`, `dim_symbol_alias`, and `fact_symbol_lineage_event` fact tables by resolving symbol changes, mergers, delistings, and multi-exchange listings.

## Inputs

- Normalized staging data from `data/staging/` (NSE master, symbol changes, ISIN mapping)
- Existing Dolt tables (dim_security_master from previous run, for incremental updates)

## Outputs

- **Curated Dimensions**: 
  - `data/curated/dim_exchange/` (NSE, BSE, etc.)
  - `data/curated/dim_issuer/` (company entities)
  - `data/curated/dim_security_master/` (securities with security_id keys)
  - `data/curated/dim_symbol_alias/` (historical ticker aliases)
- **Curated Facts**:
  - `data/curated/fact_symbol_lineage_event/` (ticker change events)
  - `data/curated/fact_listing_status_history/` (active/suspended/delisted timeline)
- **Diagnostics**: 
  - `data/staging/lineage_orphans.csv` (symbols with no matching entity)
  - `data/staging/lineage_conflicts.csv` (symbols with multiple potential mappings)
  - `data/staging/lineage_report.md` (summary of resolution decisions)

## Key Tasks

### 1. Entity Resolution (Deduplication)
- Identify unique issuers/companies by name normalization
- Resolve conflicts (same name, different ISIN vs same ISIN, different names)
- Build company entity graph (dim_issuer with unique issuer_id)
- Log conflicts for manual review if confidence <0.95

### 2. Security Master Construction
- Create one row per trading security (NSE symbol → security_id)
- Match ISIN to NSE symbol and company entity
- Resolve multi-exchange listings (NSE + BSE codes → single security)
- Flag duplicate ISINs or symbols (data quality issues)
- Set active_flag based on delisting status

### 3. Symbol Alias Resolution
- Build historical ticker chains (old_symbol → new_symbol)
- Track effective dates for each symbol version
- Distinguish current vs. historical vs. alternate ticker codes
- Handle complex transitions (A → B → C via mergers/splits)

### 4. Lineage Event Construction
- Parse symbol change announcements into structured events
- Map change types: rename, merger, split, delisting, relisting
- Extract old/new symbols, effective dates, change reasons
- Assign confidence scores based on source data quality

### 5. Listing Status Tracking
- Build effective_date timeline of status changes (active → suspended → delisted → relisted)
- Extract suspension reasons from NSE circulars
- Mark current active_flag status in dim_security_master
- Flag gaps or inconsistencies in status transitions

### 6. Quality Assurance & Reconciliation
- Validate symbol uniqueness (no duplicate tickers for different securities)
- Validate ISIN uniqueness (no ISIN mapped to multiple securities)
- Check referential integrity (all issuer_id point to dim_issuer)
- Detect orphan symbols (exist in data but no matching entity)
- Flag conflicts for manual resolution (high-touch items)

## Symbol Resolution Algorithm

```
FOR EACH NSE_SYMBOL in staging/nse_master:
  1. Look up ISIN → match to dim_issuer
  2. Check for historical symbol chains (symbol_changes table)
  3. If symbol has alias history:
     - Trace back to original security via merger/split chain
     - Build alias records (current, historical, alternate types)
  4. Assign security_id (new if first occurrence, or match existing)
  5. Validate no conflicts (symbol unique, ISIN unique per security)
  6. If conflicts detected:
     - Log to lineage_conflicts.csv
     - Flag with confidence_score < 0.95
     - Require manual approval before import
```

## Expected Artifacts

```
pipelines/lineage/
├── __init__.py
├── README.md                          # This file
├── lineage_builder.py                 # Core lineage resolution engine
├── entity_resolver.py                 # Company entity deduplication
├── symbol_resolver.py                 # Ticker chain construction
├── status_tracker.py                  # Listing status timeline builder
├── conflict_detector.py               # Identify ambiguous mappings
├── config.yaml                        # Resolution rules, confidence thresholds
├── rules/
│   ├── merger_rules.yaml              # Known merger mappings (A→B)
│   ├── delisting_rules.yaml           # Delisting effective dates
│   └── multi_exchange_rules.yaml      # NSE↔BSE cross-exchange mappings
├── requirements.txt                   # Dependencies (networkx, pandas, etc.)
└── tests/
    ├── test_entity_resolver.py
    ├── test_symbol_resolver.py
    ├── fixtures/
    │   ├── sample_symbol_changes.csv
    │   ├── sample_mergers.csv
    │   └── expected_lineage.parquet
    └── integration/
        └── test_lineage_end_to_end.py
```

## Graph Data Structure

Lineage is modeled as a directed acyclic graph (DAG):
```
INFYTEC (old) --[rename@2016-10-20]--> INFY (current)
TCS (2000) --[split@2010-06-21]--> TCSN (new code after split)
           --[reverse_split@2020-03-15]--> TCS (re-consolidated)
WIPRO --[merger_with@2018]--> WPRO (acquired by parent corp)
```

## Confidence Scoring

Each symbol mapping assigned `confidence_score` (0.0–1.0):
- **1.0**: NSE official announcement + ISIN match confirmed
- **0.95**: NSE official + inferred from data
- **0.85**: Multiple sources agree; minor ambiguity
- **0.75**: Partial data; reasonable inference; manual review recommended
- **<0.75**: Significant ambiguity; requires manual approval

## Error Cases & Handling

| Error Case | Resolution |
|-----------|-----------|
| Symbol exists in master but no lineage chain | Create with confidence=0.90 (new listing, no history) |
| Merged company; symbol disappeared | Create orphan record; mark as delisted; flag for review |
| ISIN maps to 2 different symbols | Conflict! Log to conflicts.csv; require manual merge decision |
| Delisted symbol reused for different company (2 years later) | Create separate security; validate date gap |
| Symbol change announced but not effective yet | Create scheduled lineage event (future effective date) |

## Expected Outputs

### dim_exchange
```
exchange_id | exchange_code | exchange_name | country
1           | NSE           | National Stock Exchange | India
2           | BSE           | Bombay Stock Exchange   | India
```

### dim_issuer
```
issuer_id | issuer_name           | sector        | market_cap_category | country
1         | Infosys Limited       | IT Services   | Large Cap           | India
2         | Tata Consultancy      | IT Services   | Large Cap           | India
...
```

### dim_security_master
```
security_id | nse_symbol | isin        | company_name              | issuer_id | exchange_id | listing_date | active_flag
1           | INFY       | INE009A01021| Infosys Limited           | 1         | 1           | 1999-06-11   | TRUE
2           | TCS        | INE467B01029| Tata Consultancy Services | 2         | 1           | 1999-08-25   | TRUE
...
```

### fact_symbol_lineage_event
```
lineage_id | security_id | old_symbol | new_symbol | change_date  | change_reason | merged_with_symbol
1          | 10          | WIPRO      | WIPROTECH  | 2015-01-15   | rename        | NULL
2          | 45          | HINDOIL    | NULL       | 2020-03-20   | delisting     | NULL
3          | 67          | TVSMOTORS  | TVSMM      | 2018-06-01   | merger        | TVSMOTOR
```

## SLA & Monitoring

- **Completion Time**: <10 minutes (including conflict detection)
- **Conflict Rate**: <2% of symbols (require manual review)
- **Quality Gate**: Minimum 0.90 average confidence_score
- **Validation**: All FK constraints pass; no orphan symbols in output

## Next Steps

Output from this pipeline → **adjustments/** pipeline (compute adjustment factors for price series)
