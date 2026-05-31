# India Symbol History & Corporate Actions Truth Layer

A versioned, low-cost reference data product for NSE-listed equities — solving the broken-backtest problem caused by incorrect ticker history and missing corporate action adjustments.

---

## The Problem

India equity backtests break silently. Symbols get renamed, merged, delisted, and re-listed — and most data pipelines have no record of it. Corporate actions (splits, bonuses, dividends) are either missing or applied inconsistently, producing price series that are wrong by construction.

---

## What We Provide

- **Symbol lineage** — complete rename, merger, and delisting history for NSE-listed equities
- **Corporate action events** — normalized dividend, split, bonus, rights, and merger records
- **Adjustment factors** — pre-computed multipliers for backtest-ready price series normalization
- **Security master** — active/inactive status, ISIN mappings, and identifier history
- **Monthly versioned releases** — changelogs, Dolt history, and CSV/Parquet bundles

---

## Who It's For

- Quant boutiques and fintech teams building India equity analytics
- Algorithmic traders needing trustworthy corporate action adjustments
- Data engineers fixing broken symbol histories in production pipelines
- Broker research teams maintaining backtestable price series
- Portfolio managers reconciling NAV across ticker changes

---

## How It Works

Data is extracted from official NSE sources, normalized to a canonical schema, enriched with lineage and adjustment logic, and published as versioned monthly bundles. Every record carries provenance metadata and a confidence score.

[See the methodology →](methodology.md)

---

## Delivery

Releases are shipped as CSV and Parquet bundles via private download links. No real-time API at launch — monthly versioned files with detailed changelogs.

[View pricing →](pricing.md) · [See sample queries →](sample-queries.md) · [Release notes →](release-notes.md)