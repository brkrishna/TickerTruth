# India Symbol History and Corporate Actions Truth Layer

## Mission

Provide a trustworthy, versioned reference layer for NSE symbol lineage and corporate actions to solve broken backtests and data reconciliation problems in Indian financial analytics.

## Product Scope

### What we provide
- Current and historical symbol lineage for NSE-listed equities
- Normalized corporate-action event taxonomy (splits, dividends, mergers, delistings)
- Adjustment factors for backtesting and price series normalization
- Security master with active/inactive status and identifier mappings
- Versioned monthly releases with detailed changelogs
- Sample SQL queries and usage examples

### What we don't provide (MVP)
- Real-time exchange data feeds
- Full BSE coverage in version 1
- SLA-backed uptime guarantees
- API-first delivery (file-based bundles instead)
- Automated marketplace integration

## Target Buyer

- Quant boutiques and fintech teams building India equity analytics
- Broker research teams maintaining backtestable price series
- Algorithmic traders needing trustworthy corporate action adjustments
- Data engineers fixing broken symbol histories in production pipelines
- Portfolio managers reconciling NAV across ticker changes