# Methodology and Data Model

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

## Normalization Philosophy

- **Trust over completeness**: Mark uncertain data with confidence flags rather than excluding it
- **Provenance first**: Log source and transformation for every record
- **Audit trail**: Keep all versions in Dolt for regulatory and analytical review
- **Fail gracefully**: Missing data is better than wrong data; log gaps explicitly

## Data Model Rationale

### Dimension Tables

**dim_exchange**
- Low-cardinality reference for NSE, BSE, etc.
- Enables multi-exchange support in future phases
- Single record per exchange; minimal updates

**dim_issuer**
- Core company/issuer identity
- Stores sector, market cap category for buyer segmentation
- UNIQUE constraint on issuer_name prevents dual issuers
- Updated only when issuer metadata changes

**dim_security_master**
- Central security identifier hub
- NSE symbol as primary lookup key (UNIQUE)
- ISIN for cross-exchange reconciliation
- Surrogate key (security_id) for efficient foreign keys
- active_flag enables soft delisting without row deletion

**dim_symbol_alias**
- Tracks all historical symbols for a security
- alias_type distinguishes current vs. historical vs. alternate codes
- effective_from/to enables date-range lookups
- Supports symbol rename, ticker migration, multi-listing scenarios

**dim_corporate_action_type**
- Immutable lookup table (SPLIT, DIVIDEND, BONUS, MERGER, etc.)
- Public domain knowledge; rarely changes
- Ensures consistent action classification across all events

### Fact Tables

**fact_equity_eod**
- End-of-day price snapshots (OHLCV)
- UNIQUE on (security_id, trading_date) prevents duplicates
- High-cardinality table; volume is expected to grow large
- Optional prices (open, high, low) allow missing data gracefully

**fact_corporate_action_event**
- Core event store for corporate actions
- action_type_id links to lookup table for consistency
- old_value / new_value are flexible (e.g., old shares / new shares for splits, dividend amount for dividends)
- adjustment_factor is pre-computed (split ratio, dividend yield, bonus ratio)
- confidence_score (0.0 to 1.0) flags uncertain or estimated events
- Multiple date fields support different event definitions (announcement, record, payment)

**fact_adjustment_factor**
- Pre-computed cumulative adjustments for backtesting
- One row per (security, date) for fast lookups
- Separates split, dividend, and bonus adjustments for transparency
- total_adjustment_factor = split × dividend × bonus (for easy reversed price calculation)
- Lazy-updated: computed only on data refresh, not real-time

**fact_symbol_lineage_event**
- Tracks ticker and name changes over time
- change_reason is constrained to predefined values (rename, merger, split, delisting, relisting)
- merged_with_symbol captures merger targets for research
- Enables reconstruction of historical symbol chains for backtesting

**fact_listing_status_history**
- Tracks active, suspended, delisted, relisted states
- effective_date denotes when status changes took effect
- reason field logs corporate announcements or regulatory actions
- Enables survivorship-bias-aware portfolio analysis

### Key Design Principles

1. **Surrogate keys for all tables** — Decouples logical identity from business keys
2. **Soft deletes via flags** — Keep historical records for audit trails (active_flag)
3. **Temporal tracking** — created_at and updated_at on all dimension/fact tables enable change data capture
4. **Flexible fact granularity** — old_value/new_value design supports multiple action types without separate fact tables
5. **Confidence scoring** — confidence_score on events allows buyers to filter by data quality
6. **Layered constraints** — NOT NULL on critical fields, FOREIGN KEYs for referential integrity, UNIQUE on natural keys to prevent duplicates

---

## Source Inventory

### NSE Official Sources

#### Equity Master Data (Security Master)

**URL Pattern:**
```
https://www.nseindia.com/uls/datafiles/EQUITY_L.csv
https://www.nseindia.com/uls/datafiles/EQUITY_L.txt (alternative pipe-delimited format)
```

**Raw Format & Fields:**
```
Pipe-delimited (|) or CSV
Fields: ISIN | SYMBOL | NAME | SERIES | DATE_OF_LISTING | PAID_UP_VALUE | 
        MARKET_LOT | ISE_LISTED | FACE_VALUE | CATEGORY | INDUSTRY_NAME | 
        YTD_HIGH | YTD_LOW | MKTCAP | PRICE
```

**Refresh Frequency:**
- Updated daily (end of business day, ~5:30 PM IST)
- New listings added same day
- Delisting updates applied immediately

**Anticipated Quality Issues:**
- **Duplicate entries**: Occassional duplicate rows for same symbol in monthly archives (reconcile by latest date)
- **Encoding issues**: Legacy data may have non-UTF8 characters (requires sanitization)
- **Price anomalies**: YTD_HIGH/LOW may include corporate action-unadjusted prices
- **Missing fields**: Older archives (pre-2010) may lack MARKET_LOT or CATEGORY
- **Delisting lag**: Delisted symbols may remain in file 2-3 business days after delisting notice
- **Sector changes**: INDUSTRY_NAME updates lag official sector classification changes by 1-2 days

**Storage Location:** `data/raw/nse/master/`
**Expected File Size:** ~500 KB per day
**Backup Strategy:** Retain daily snapshots for 2 years (13 months rolling)

---

#### NSE Archives & Historical EOD Data

**URL Pattern:**
```
https://www.nseindia.com/uls/datafiles/EQUITY_${YYYYMMDD}.zip (daily bulk export)
https://www1.nseindia.com/Content/Historical/EQUITIES/${YYYY}/${SYMBOL}_${DDMMMYYYY}.csv (per-symbol historical)
```

**Raw Format & Fields:**
```
CSV format
Fields: SYMBOL | DATE | OPEN | HIGH | LOW | CLOSE | VOLUME | VALUE | TURNOVER
Alternative header (older format): SYMBOL,OPEN,HIGH,LOW,CLOSE,VOLUME,VALUE

Date format: DD-MMM-YYYY (e.g., 28-May-2024)
Prices: DECIMAL(10,2) in INR
Volume: INTEGER (number of shares)
Value: DECIMAL(15,2) in INR (open × volume / close approx)
Turnover: DECIMAL(10,2) percentage
```

**Refresh Frequency:**
- Daily extraction for current trading date (available T+0 post-market close)
- Historical data: Complete dataset available for download (Jan 2000 onwards)
- Backfill extractions: Monthly complete export available ~7th of each month

**Anticipated Quality Issues:**
- **Missing holidays**: Holidays and trading halts result in gaps (data will show no row for that date)
- **Splits & bonus unadjusted**: Historical prices not pre-adjusted for splits/bonuses
- **Zero volume days**: Illiquid stocks may show 0 volume on low-liquidity days (valid, not an error)
- **Weekend data**: Weekend trading data only for select derivative-driven instruments (not typical equities)
- **Data corrections**: NSE occasionally corrects prices for trades executed in error (restatement lag 1-5 days)
- **Extreme prices**: Penny stocks may show OHLC spanning 100%+ range in single day (valid)
- **Suspended stocks**: Suspended symbols' prices remain frozen until re-listing (can cause stale data detection to fail)

**Storage Location:** `data/raw/nse/eod/`
**Expected File Size:** ~10-15 MB per daily export; ~2 GB per year aggregate
**Retention:** Perpetual (required for backtesting)

---

#### Corporate Action Announcements

**URL Pattern:**
```
https://www.nseindia.com/corporates/datafiles/CAlist.jsp (live board with filters)
https://www.nseindia.com/corporates/datafiles/ca_isin_${YYYYMM}.zip (monthly archive)
https://www.nseindia.com/corporates/bodheading.jsp (detailed announcement page per action)
```

**Raw Format & Fields:**
```
HTML table parsed from web portal OR CSV export:
Fields: ISIN | SYMBOL | COMPANY_NAME | PURPOSE | EX_DATE | REC_DATE | 
        PAYMENT_DATE | DIVIDEND_AMT | NEW_RATIO | OLD_RATIO | BONUS_RATIO | 
        ANNOUNCEMENT_DATE | APPROVAL_DATE | CIRCULATION_DATE

Purpose: ENUM('Dividend', 'Bonus', 'Split', 'RightIssue', 'Demerger', 'Merger', 
              'Delisting', 'NameChange', 'CreditSplit', 'ISINChange')
Ratios: DECIMAL(10,6) (e.g., 1:2 split = 2.0 ratio)
Amounts: DECIMAL(10,2) per share in INR
Dates: DD-MMM-YYYY format
```

**Refresh Frequency:**
- Real-time: Announcements posted as board-approved
- Live board updated every 2 hours (9:30 AM to 4:00 PM IST on trading days)
- Monthly archives finalized ~5th of following month
- Quarterly/annual: Special dividend announcements may cluster post-earnings

**Anticipated Quality Issues:**
- **Date inconsistencies**: Announcement_date ≠ Approval_date ≠ Circulation_date (clarify which is authoritative)
- **Delayed updates**: Delisting notices sometimes posted 24-48 hours after board decision
- **Web parsing errors**: HTML structure changes may break scraper; commas in company names break CSV parsing
- **Dividend ratio ambiguity**: Bonus and split terminology used inconsistently (e.g., "2:1 split" vs "2:1 bonus")
- **Historical gaps**: Pre-2015 announcements partially archived; some records unavailable online
- **Cancelled actions**: Approved but later-cancelled actions may remain on live board without indication
- **Typos in amounts**: Dividend amounts transcribed manually; occasional 10x/100x errors (1.50 INR vs 15.0 INR)
- **Missing detail**: Some announcements lack PAYMENT_DATE or REC_DATE (only EX_DATE specified)
- **Multiple announcements per action**: Large reorganizations may split into multiple rows per corporate action

**Storage Location:** `data/raw/nse/corporate_actions/`
**Expected File Size:** ~5-10 MB per monthly archive; ~20-30 per year
**Quality Check:** Flag all dividend amounts > 50 INR per share (likely data entry error)

---

#### Symbol Changes & Name Updates

**URL Pattern:**
```
https://www.nseindia.com/corporates/corporates_ca_renames.jsp (ticker rename board)
https://www.nseindia.com/corporates/datafiles/symbol_changes_${YYYY}.txt (annual archive)
https://www.nseindia.com/DownloadCenter (SEBI delisting/relisting circulars)
```

**Raw Format & Fields:**
```
Text file or HTML table
Fields: OLD_SYMBOL | NEW_SYMBOL | CHANGE_DATE | CHANGE_TYPE | REASON | 
        CIRCULAR_NO | ISIN_CHANGE_FLAG | NOTES

Change_type: ENUM('Rename', 'Merger', 'Demerger', 'Split', 'Relisting', 'Delisting', 'Relabel')
ISIN_Change_flag: BOOLEAN (Y/N) - indicates if ISIN also changed during transition
```

**Refresh Frequency:**
- Real-time: Changes announced in NSE circulars (typically effective date is T+2 to T+30)
- Board updated same day of announcement
- Annual archive compiled ~15th of January following year
- Delisting/relisting notices updated within 1 business day

**Anticipated Quality Issues:**
- **Delayed circulars**: Official circular sometimes trails market implementation by 1-3 days
- **Effective date ambiguity**: "Effective date" vs "Commencement date" vs "Ex-date" terminology inconsistent
- **Merger consolidation gaps**: Multi-leg mergers (A → B → C) may have incomplete middle transition records
- **Relisting timing**: Delisted → Relisted transitions have gap periods with no price data (valid; not tradeable)
- **Symbol reuse**: Rare case where old symbol reused for different security years later (conflicts in reconciliation)
- **Missing old symbols**: Pre-1999 ticker changes not fully digitized in NSE archive
- **ISIN stability**: Some demergers result in old ISIN retained with new symbol (confuses lookups if not flagged)

**Storage Location:** `data/raw/nse/symbol_changes/`
**Expected File Size:** ~500 KB per year (highly volatile — reorganization years may be 2-3 MB)
**Retention Strategy:** Perpetual (critical for historical symbol resolution)

### Ticker Mapping & Cross-References

#### ISIN-Symbol Mapping (NSDL Registry)

**URL Pattern:**
```
https://www.nsdl.co.in/securities/
https://www.nsdl.co.in/datafiles/isin_master_${YYYYMMDD}.zip (bulk export, monthly)
```

**Raw Format & Fields:**
```
Tab-delimited or CSV
Fields: ISIN | ISIN_TYPE | SECURITY_NAME | NSE_SYMBOL | BSE_CODE | 
        LISTING_DATE | EXPIRY_DATE | SECURITY_STATUS | ISSUER_ID | 
        CUSTODIAN_ID | DEPOSITORY_ID | DEMAT_FLAG | ISIN_CATEGORY

ISIN format: INxx9999xxxx (12-char alphanumeric)
ISIN_TYPE: ENUM('Equity', 'Debt', 'MutualFund', 'Preference', 'Rights', 'Warrants')
Security_status: ENUM('Active', 'Suspended', 'Delisted', 'Inactive')
Demat_flag: BOOLEAN dematerialization eligibility
```

**Refresh Frequency:**
- Quarterly bulk export (typically mid-month)
- Real-time web updates for new ISIN issuance
- Delisting/relisting updates posted within 2 business days of NSE announcement

**Anticipated Quality Issues:**
- **Historical ISIN gaps**: Pre-2003 equities may lack digitized ISIN data
- **Dual-listing mismatches**: BSE_CODE may differ from NSE_SYMBOL for same security; reconciliation required
- **Expired ISINs**: Delisted securities may retain active ISIN for 1-2 months post-delisting
- **Multiple ISINs per symbol**: Rare but happens (e.g., company issued multiple ISIN tranches)
- **Typos in BSE codes**: BSE codes transcribed manually; occasional digit transposition
- **Bulk file delays**: Quarterly export sometimes delayed 2-3 weeks after announcement
- **Status staleness**: Suspension/delisting status lags NSE effective date by 1-5 business days

**Storage Location:** `data/raw/nsdl/`
**Expected File Size:** ~200 MB per quarterly export (includes all ISIN types)
**Retention:** Perpetual (ISIN immutable once assigned)

---

#### BSE Ticker Reference (Multi-Exchange Support)

**URL Pattern:**
```
https://www.bseindia.com/corporates/ScripMaster.html (web portal)
https://www.bseindia.com/datafiles/bse_equities_${YYYYMMDD}.csv (daily download)
```

**Raw Format & Fields:**
```
CSV format
Fields: BSE_CODE | BSE_SYMBOL | NSE_SYMBOL | ISIN | COMPANY_NAME | 
        SECTOR | INDUSTRY | LISTING_DATE | FACE_VALUE | MARKET_LOT | 
        STATUS | SECURITY_TYPE

Status: ENUM('Active', 'Suspended', 'Delisted')
Face_value: DECIMAL(10,2) in INR (e.g., 1.00, 5.00, 10.00, 100.00)
```

**Refresh Frequency:**
- Daily (updated end of trading day)
- New listings added same day as NSE (or 1-2 days later if BSE-only listing)

**Anticipated Quality Issues:**
- **Cross-listing gaps**: Few equities listed only on BSE (no NSE_SYMBOL); reconciliation required
- **Symbol divergence**: BSE_SYMBOL and NSE_SYMBOL may differ for same security (both valid, requires mapping)
- **Stale status**: Delisting/suspension status may lag NSE by 3-5 business days
- **Face value inconsistency**: Some companies show different face values on BSE vs. NSE records (legacy data quality issue)
- **Incomplete sector data**: Older listings may lack INDUSTRY field
- **File encoding**: Legacy files sometimes use non-UTF8 encoding (Latin-1)

**Storage Location:** `data/raw/bse/` (reserved for phase 2 multi-exchange support)
**Expected File Size:** ~3-5 MB per daily export
**Status:** Currently not actively extracted; recommended for Q3 2026 integration

---

### Third-Party Data Sources (Premium Feeds - Optional)

#### Thomson Reuters/Refinitiv

**URL Pattern:**
```
API endpoint: https://api.refinitiv.com/data/historical/ (requires enterprise license)
Data feed: RIC instrument codes for NSE equities
```

**Raw Format & Fields:**
```
JSON API response
Fields: RIC | NSE_SYMBOL | ISIN | SECURITY_NAME | CUSIP | 
        EXCHANGE_CODE | LISTING_STATUS | COMPANY_ID | SECTOR | 
        INDUSTRY_CLASSIFICATION

RIC format: NSExxxxx.NS (e.g., INFY.NS, TCS.NS)
Sector/Industry: Standardized classification system
```

**Refresh Frequency:**
- Real-time data feed (streamed during market hours)
- EOD batch import (available T+1)
- Corporate action metadata: T+0 (announcement day)

**Anticipated Quality Issues:**
- **RIC-NSE mapping gaps**: ~5-10% of small-cap equities lack standardized RIC codes
- **Sector classification lag**: Q1 classifications available Q1+30 days
- **Premium subscription required**: Limits access to data engineering team only
- **Blackout periods**: Some corporate actions embargoed until official NSE announcement

**Status:** Currently not in use; recommended for high-confidence corporate action scoring
**Estimated Cost:** ~$10K-50K per year for enterprise feed
**Integration Timeline:** Feasible Q4 2026 for premium tier offerings

---

#### Bloomberg Terminal (Optional Premium)

**URL Pattern:**
```
Terminal function: /BI (Bloomberg Industry classification)
Ticker code: Xxxx IN (NSE equity format in Bloomberg, e.g., INFY IN, TCS IN)
```

**Raw Format & Fields:**
```
Binary Bloomberg format (proprietary) or exported CSV
Fields: TICKER | NAME | SECTOR | INDUSTRY | MARKET_CAP | EPS | 
        DIVIDEND_YIELD | 52_WEEK_HIGH | 52_WEEK_LOW | ANALYST_CONSENSUS | 
        RECENT_NEWS

Updated from: Bloomberg Research, company filings, broker estimates
```

**Refresh Frequency:**
- Intraday: Market data updates during trading hours
- EOD: Consensus estimates updated daily
- Corporate actions: Announced on Bloomberg terminals T+0

**Anticipated Quality Issues:**
- **Analyst bias**: Consensus affected by sell-side bias; tech stocks may be overweighted
- **Earnings data lag**: FY earnings availability delays 1-2 weeks post-announcement
- **Terminal downtime**: Bloomberg outages affect real-time data access (rare but possible)
- **Access restrictions**: User-level licensing limits deployment to specific terminals

**Status:** Not currently integrated; terminal license required
**Access Model:** Requires Bloomberg Terminal subscription (~$24K per terminal per year)
**Use Case:** Optional for buyers requiring analyst consensus and news integration

---

### Data Quality & Confidence Scoring Framework

#### High Confidence Sources (score ≥ 0.95)
- **NSE EOD OHLCV** (live trading data, published same day)
- **NSE Corporate Action Board** (official announcements, immutable post-publication)
- **NSDL ISIN Registry** (government-backed central registry, immutable)

#### Medium Confidence Sources (score 0.7–0.95)
- **NSE Historical archives** (subject to corrections, restatements possible T+1 to T+5)
- **Parsed web content** (OCR/text extraction may introduce errors, requires validation)
- **BSE cross-references** (reconciliation required with NSE; may have reconciliation gaps)
- **Reconstructed lineage** (assembled from multiple announcements; chain-of-custody risk)

#### Low Confidence Sources (score < 0.7)
- **User-submitted corrections** (pending independent validation)
- **Third-party news feeds** (may report rumors before official confirmation)
- **Estimated adjustment factors** (computed estimates when exact data unavailable)
- **Thomson Reuters/Bloomberg** (subject to terminal availability and licensing delays)

---

### Data Pipeline Architecture

```
NSE Official → Raw Data Layer (data/raw/)
    ↓
Parsing & Validation → Staging Layer (data/staging/)
    ↓
Normalization & Enrichment → Curated Layer (data/curated/)
    ↓
Dolt Repository (Version Control & Audit Trail)
    ↓
Public Release (CSV/Parquet exports)
```

### Update Frequency & SLAs

| Source | Update Frequency | Latency | Retention |
|--------|------------------|---------|-----------|
| NSE EOD Prices | Daily (after market close ~5:30 PM IST) | T+1 | 25+ years |
| Corporate Actions | Real-time (as announced) | T+0 | Perpetual |
| Symbol Changes | Real-time (as notified) | T+0 | Perpetual |
| ISIN Master | Quarterly refresh | T+30 | Perpetual |

### Access & Licensing

- **NSE Public Data**: Free for research/non-commercial use
- **Dolt Repository**: Version-controlled; full audit trail available
- **Curated Exports**: Available under specified licensing terms per buyer agreement
- **Raw Data Attribution**: All sources credited in metadata; derivative analysis permitted with attribution