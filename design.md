# India Symbol History and Corporate Actions Truth Layer — Design

## 1. Overview

This document defines the MVP technical design and boundary conditions for the India corporate-actions and symbol-history truth layer.

The product is built as a versioned reference-data offering using Python-led ETL, Dolt versioned tables, Cloudflare Pages for docs, and Cloudflare R2 for artifacts.

## 2. Architecture

- `pipelines/` contains ETL jobs:
  - `extract/` pulls NSE archives and corporate action source data.
  - `normalize/` converts raw source fields to canonical schemas.
  - `lineage/` produces ticker and corporate-action lineage.
  - `adjustments/` calculates backtest adjustment factors.
  - `publish/` writes artifacts, updates Dolt, and uploads release bundles.
- `dolt/` stores schema definitions, seed data, and migration files.
- `data/` stores raw, staged, curated, and sample artifacts.
- `website/` hosts the public landing page and docs.
- `releases/` stores monthly bundles, changelogs, and published exports.

## 3. MVP Stack

- Python 3.x with:
  - `pandas`, `numpy`, `pyarrow`
  - `SQLAlchemy` or direct SQL for Dolt
  - `requests`, `BeautifulSoup`, or `Playwright` for source extraction
  - `pytest` for tests
- Dolt / DoltHub for versioned data and history tracking
- Cloudflare Pages for public site and docs
- Cloudflare R2 for downloadable CSV/Parquet release artifacts
- GitHub repo as the code and documentation source
- GitHub Actions for CI, scheduled workflows, and deployment automation

## 4. Data Model

### Core dimension tables
- `dim_security_master`
- `dim_issuer`
- `dim_exchange`
- `dim_symbol_alias`
- `dim_corporate_action_type`

### Core fact tables
- `fact_equity_eod`
- `fact_corporate_action_event`
- `fact_adjustment_factor`
- `fact_symbol_lineage_event`
- `fact_listing_status_history`

### Sample public views
- `vw_security_current`
- `vw_symbol_lineage_sample`
- `vw_action_timeline_sample`
- `vw_adjusted_price_reference_sample`

## 5. Delivery Model

- Public sample release via Cloudflare Pages and R2
- Paid bundle delivery via private R2 links and/or DoltHub access
- Release notes and version history in `docs/release-notes.md`
- Manual commercial onboarding until payment/fulfillment is automated

## 6. Boundary Conditions and Non-Goals

### Included in MVP
- NSE-listed equities symbol history and corporate actions
- Normalized corporate-action event table
- Adjustment factors for backtesting
- Security master with active/inactive status
- Release notes and versioned bundles
- Sample SQL and CSV/Parquet exports

### Excluded from MVP
- Real-time exchange-level data
- Full BSE coverage in initial release
- SLA-backed enterprise uptime guarantees
- API-first delivery model at launch
- Marketplace-native billing or automated subscriptions in phase 1

## 7. Constraints and Assumptions

- Minimal infrastructure cost is critical
- Manual commercial delivery is acceptable early on
- Source data quality will be imperfect and requires QA
- GitHub Actions should handle repeatable automation
- Cloudflare R2 is used for low-cost distribution and storage

## 8. Quality and Validation Controls

- Schema validation for every data load
- Data quality checks for missing keys, duplicates, and invalid dates
- Lineage cycle detection and company rename consistency
- Adjustment factor sanity checks and provenance logging
- Smoke tests for export generation and artifact creation

## 9. Future Migration Paths

- Keep export logic decoupled from delivery channel
- Store schema and sample queries for Snowflake/Databricks migration
- Use Dolt history as an audit trail for later data warehouse onboarding
