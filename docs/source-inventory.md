# NSE Data Sources Inventory

## Purpose

This document catalogs all National Stock Exchange (NSE) data sources used in Phase 2 (Data ingestion and normalization). It specifies source URLs, formats, access methods, expected schemas, and data quality notes.

## 1. Historical Equity Symbol List & Listing Calendar

| Attribute | Value |
|-----------|-------|
| **Source Name** | NSE Listed Companies Master Database |
| **Primary URL** | https://www.nseindia.com/companies-listing/corporate-filings-application |
| **Data Portal URL** | https://www.nseindia.com/all-reports |
| **Format** | CSV (via exports) / HTML (web interface) |
| **Frequency** | Daily updates |
| **Access Method** | Web scraping or direct CSV download from NSE data portal |
| **Tool Recommendations** | BeautifulSoup, Playwright for scraping; pandas for CSV parsing |
| **Historical Depth** | ~1994 onwards (NSE inception) |

### Key Fields Available

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| Symbol | string | Trading symbol on NSE | May include series suffix (-EQ, -REPL) |
| Company Name | string | Legal company name | May have variants over time |
| ISIN | string | 12-character international security ID | Stable identifier across renames |
| Industry / Sector | string | NSE sector classification | e.g., BANKING, IT, PHARMA |
| Series | string | Security series | Typically "EQ" for equities |
| Listing Date | date | First trading date on NSE | Format: DD-MM-YYYY |
| Maturity Date | date | Last trading date (if delisted) | NULL for active securities |
| Trading Status | enum | Current status | ACTIVE \| SUSPENDED \| DELISTED |
| Market Cap (optional) | decimal | Market capitalization | May be available in some exports |

### Expected Output Schema (dim_security_master)


### Extraction Notes

- NSE maintains a searchable database; no bulk API currently available for public use
- Download via: https://www.nseindia.com/all-reports → Equity section → Equity Master / Listing Calendar
- Alternative: Scrape company listing pages with symbol filter
- For historical snapshots, maintain archives of weekly extracts
- Deduplicate on [symbol, listing_date] before merge

---

## 2. Corporate Action Announcements (Dividends, Splits, Bonus, Rights, Mergers, Delistings)

| Attribute | Value |
|-----------|-------|
| **Source Name** | NSE Corporate Actions & Board Meetings |
| **Primary URL** | https://www.nseindia.com/companies-listing/corporate-filings-actions |
| **Alternative URL** | https://www.nseindia.com/companies-listing/corporate-filings-board-meetings |
| **Format** | HTML tables + PDF announcements |
| **Frequency** | Real-time (as announcements published) |
| **Access Method** | Web scraping HTML + PDF text extraction |
| **Tool Recommendations** | Selenium/Playwright for dynamic content, PyPDF2 or pdfplumber for PDF parsing |
| **Historical Depth** | ~15+ years of archives available |

### Key Fields Available

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| Symbol | string | Trading symbol | Must match dim_security_master |
| Announcement Date | date | When NSE published the action | Format: DD-MM-YYYY |
| Ex Date | date | First day without entitlement | Critical for backtest accuracy |
| Record Date | date | Cutoff for entitlement holders | Usually 7-10 days after ex_date |
| Payment Date | date | When benefits are credited | May be 1-3 months after record_date |
| Action Type | enum | Category of action | DIVIDEND, SPLIT, BONUS, RIGHTS, MERGER, DELISTING, NAMECHANGE |
| Value / Ratio | string/decimal | Benefit amount or ratio | e.g., "₹5 per share" or "1:2 split" |
| Units | string | Unit of measurement | "Re/Rs" for dividends, ratio for splits |
| Frequency | enum | Timing of dividend | INTERIM, FINAL, SPECIAL |
| PDF Link | string | URL to announcement PDF | Contains detailed terms and conditions |
| Status | enum | Action status | APPROVED, EX-DATE-PASSED, COMPLETED, POSTPONED |

### Expected Output Schema (fact_corporate_action_event)


### Extraction Notes

- NSE corporate actions page is dynamically loaded; use Selenium or Playwright
- Filter by symbol and date range to avoid overwhelming data
- PDFs contain structured announcements; extract key dates and ratios using regex patterns
- Common patterns:
  - "With effect from {date}" → ex_date or payment_date
  - "Ratio {num}:{denom}" → split/bonus ratio
  - "₹{amount}" → dividend amount
- For complex actions (mergers, rights), may require manual verification from PDF
- Create quality flag if parsing confidence < 0.8

---

## 3. NSE Equity Bhavcopy (Daily End-of-Day Trade Data)

| Attribute | Value |
|-----------|-------|
| **Source Name** | NSE Equity Bhavcopy (EOD Market Data) |
| **URL** | https://www.nseindia.com/all-reports → Reports section |
| **Format** | ZIP file containing CSV |
| **Frequency** | Daily (published after market close, ~6 PM IST) |
| **Access Method** | HTTP download or FTP pull from NSE reports server |
| **Tool Recommendations** | requests library, zipfile, pandas |
| **Historical Depth** | ~2000 onwards |

### Key Fields Available

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| Symbol | string | Trading symbol | Matches dim_security_master ticker |
| Date | date | Trading date | Format: DD-MMM-YYYY |
| Open | decimal | Opening price | First traded price of the day |
| High | decimal | Highest price | Intraday high |
| Low | decimal | Lowest price | Intraday low |
| Close | decimal | Closing price | Last traded price of the day |
| Last | decimal | Last traded price | May differ from close |
| Prev Close | decimal | Previous day's close | For day-over-day change calc |
| Volume | integer | Total shares traded | In quantity (not value) |
| Value | decimal | Total trade value | In rupees |
| No of Trades | integer | Count of transactions | Market depth indicator |

### Use Case in Phase 2

- **Price gap validation** for adjustment factor calculation
- Cross-check if stock split adjustment matches actual price jump
- Detect trading halts or anomalies (zero volume)
- Verify date consistency in corporate action events

### Data Quality Notes

- Bhavcopy is the official NSE EOD reference
- All securities in the file are valid trading symbols
- Volume may be zero on suspension/delisting dates
- Prices are adjusted for splits/bonus within daily prices but not across days

---

## 4. NSE Circulars & Announcements (Name Changes, Status Changes, Delistings)

| Attribute | Value |
|-----------|-------|
| **Source Name** | NSE Exchange Communications - Circulars & Announcements |
| **Primary URL** | https://www.nseindia.com/resources/exchange-communication-circulars |
| **Alternative URL** | https://www.nseindia.com/resources/exchange-communication-press-releases |
| **Format** | HTML circulars (PDF documents) |
| **Frequency** | Real-time (as events occur) |
| **Access Method** | Web scraping with keyword filtering |
| **Tool Recommendations** | BeautifulSoup, regex for pattern matching, PDF extraction |
| **Historical Depth** | Full archive available; ~10-20+ years |

### Key Fields to Extract

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| Circular Number | string | NSE circular ID | e.g., "NSE/CMPT/45678" |
| Circular Date | date | Publication date | |
| Symbol | string | Affected symbol | |
| Old Symbol | string | Previous symbol (if renamed) | NULL if not applicable |
| New Symbol | string | New symbol (if renamed) | NULL if not applicable |
| Old Name | string | Previous company name | |
| New Name | string | New company name | |
| Event Type | enum | RENAME, DELISTING, SUSPENSION, REACTIVATION, MERGER, DEMERGER |
| Effective Date | date | Date action takes effect | "With effect from {date}" |
| Reason | string | Explanation from NSE | May be prose text |
| PDF Link | string | URL to full circular | For manual verification |

### Expected Output Schema (lineage_raw_extract)


### Extraction Notes

- NSE circulars are unstructured; use regex patterns for key information:
  - `r"renamed?\s+(?:as|to)\s+([A-Z0-9]+)"` → new symbol
  - `r"delisted?\s+(?:w\.e\.f|with\s+effect\s+from)\s+(\d{2}-\d{2}-\d{4})"` → delisting date
  - `r"merged?\s+with\s+([A-Za-z0-9\s]+)"` → merger details
- For complex renames or mergers, flag for manual review
- Store original PDF link for verification
- Document any ambiguities in quality_issues report

---

## 5. Historical Archives & Indices Data

| Attribute | Value |
|-----------|-------|
| **Source Name** | NSE Indices Historical Data |
| **URL** | https://www.nseindia.com/reports-indices-historical-index-data |
| **Format** | CSV exports |
| **Frequency** | Historical snapshot (no live updates) |
| **Access Method** | Manual download or batch API (if available) |
| **Use Case** | Backfill historical symbol lists, validate index constituents |

### Data Quality Caveats

- Indices data may only include constituents, not full NSE universe
- Use as validation reference, not primary source
- Better for cross-checking symbol lists than as primary feed

---

## Data Extraction Workflow (Phase 2 Schedule)

### Weekly Cadence (Recommended)


---

## Known Challenges & Mitigations

| Challenge | Mitigation Strategy |
|---|---|
| **Corporate action PDFs have inconsistent formats** | Use keyword regex patterns + fuzzy matching; maintain manual review queue for low-confidence extractions |
| **Symbol suffixes vary (-EQ, -REPL, -ISIN)** | Create explicit normalization rules in field_mappings.yaml; test against known symbols |
| **Delistings sometimes silent** (symbol stops appearing in lists) | Track symbol presence over time; flag gaps as potential delistings; cross-reference with circulars |
| **Company names have special characters & variants** | Store both original and normalized versions; use fuzzy string matching for company rename detection |
| **Historical data gaps or format changes over decades** | Document data availability by date range; seed with known historical mappings; use ISIN as stable anchor |
| **Web scraping rate limits & blocks** | Use rotating delays (2-5 seconds between requests), rotate user-agents, respect robots.txt, cache pages |
| **PDF parsing fails on scanned documents** | Use OCR (Tesseract, AWS Textract) as fallback; flag for manual review if OCR confidence < 0.7 |
| **Circular announcements use ambiguous language** | Create a decision tree for common phrases; document assumptions; ask subject matter experts to review edge cases |

---

## Data Completeness Targets

For MVP success, aim for these coverage levels by end of Phase 2:

- **Symbol Master:** 95%+ coverage of all NSE-listed equities (current + delisted)
- **Corporate Actions:** 90%+ coverage of major events (dividends, splits, bonus, mergers) for last 10 years
- **Lineage Events:** 85%+ confidence for renames and delistings; 70%+ for complex mergers/demergers
- **Adjustment Factors:** 95%+ coverage for splits/bonus; 80%+ coverage for complex rights offerings

---

## References & Further Reading

- **NSE Official Data Download:** https://www.nseindia.com/all-reports
- **NSE Circulars Archive:** https://www.nseindia.com/resources/exchange-communication-circulars
- **NSE Corporate Filings:** https://www.nseindia.com/companies-listing/corporate-filings-application
- **NSE Data & Analytics:** https://www.nseindia.com/nse-data-and-analytics (for paid data feeds)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-30 | Initial source inventory for Phase 2 |
