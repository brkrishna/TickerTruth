# TickerTruth — India Symbol History & Corporate Actions Truth Layer

**[tickertruth.com](https://tickertruth.com/?utm_source=github&utm_medium=readme&utm_campaign=readme-launch)** — versioned reference data for NSE (and BSE) equities: symbol lineage, corporate actions, and backtest adjustment factors.

---

## The problem

India equity backtests silently break. Symbols get renamed, merged, or relisted without a clean audit trail. Corporate actions (splits, bonuses, dividends) are scattered across exchange dumps with inconsistent formatting. Most retail data vendors paper over the gaps; they don't surface the lineage.

If you've ever seen a backtest blow up on a stale ticker or a missed split — this is what TickerTruth fixes.

---

## What's in the data

| Table | Description |
|---|---|
| `dim_security_master` | Full NSE/BSE security master with ISIN, series, status |
| `dim_issuer` | Canonical issuer registry (deduped across exchanges) |
| `dim_symbol_alias` | All known symbol names a security has traded under |
| `fact_symbol_lineage_event` | LISTING / DELISTING / RENAME events with ISIN-verified confidence |
| `fact_corporate_action_event` | Splits, bonuses, dividends, rights — normalized to canonical types |
| `fact_adjustment_factor` | Cumulative backward price-adjustment factors per event |
| `fact_listing_status_history` | Exchange status changes over time |

Sample views (`vw_symbol_lineage_sample`, `vw_adjusted_price_reference_sample`, etc.) are available in the free tier.

---

## Methodology

### Symbol lineage detection
The `SymbolLinker` compares NSE symbol snapshots across periods and detects:
- **LISTING** — new ISIN appears
- **DELISTING** — ISIN absent from current snapshot, absent from known aliases
- **RENAME** — same ISIN, different symbol string

Confidence is scored from 0–1. Events corroborated by a corporate action within ±30 days receive a +0.15 boost. Only events above the configured threshold (default 0.6) are included in the curated output.

### Corporate action normalization
Raw NSE/BSE action strings are mapped to a canonical action type vocabulary via `field_mappings.yaml`. Each action record carries:
- `action_type` — one of `SPLIT`, `BONUS`, `DIVIDEND`, `RIGHTS`, `MERGER`, `REVERSE_SPLIT`
- `ratio_numerator` / `ratio_denominator` — parsed from exchange notation
- `ex_date`, `record_date`, `payment_date`
- `confidence_flag` — `HIGH`, `MEDIUM`, or `LOW`

### Adjustment factors
Backward cumulative adjustment factors are chained from the most recent event to the earliest. The `AdjustmentFactorBuilder` validates that each factor chain satisfies:  
`total_factor = product(split_factors) × product(bonus_factors)`  
No duplicate `(security_id, as_of_date)` pairs are allowed in the output.

### Quality scoring
Every record gets a `data_quality_score` (0–1) and a `confidence_flag`. Scores are derived from field completeness, cross-source corroboration, and action-type parseability. The pipeline halts if the curated output fails post-import QA checks.

---

## Delivery model

| Tier | Contents | Access |
|---|---|---|
| Free sample | Public views, 90-day slice | tickertruth.com / GitHub |
| Paid bundle | Full history CSV + Parquet, Dolt access | Manual purchase → private R2 link |

Releases ship monthly. Each release is tagged (`v2026.MM.DD`) in Dolt and accompanied by release notes in `releases/`.

---

## Data flow

```
NSE/BSE (live)
    │
    ▼
data/raw/                 ← daily snapshots, never modified
    │
    ▼
data/staging/             ← consolidated, deduplicated
    │
    ▼
data/curated/             ← canonical schema CSVs
    │
    ▼
dolt/                     ← versioned tabular release (tagged)
    │
    ▼
Cloudflare R2             ← downloadable bundles (free + paid)
```

Pipeline stages: `extract → normalize → lineage → adjust → validate → load → export → manifest → release-notes → website`

---

## Tech stack

- Python 3.11+ · pandas · pytest · ruff
- [Dolt](https://github.com/dolthub/dolt) — Git for data
- Cloudflare Pages + R2 — static delivery, artifact storage
- GitHub Actions — CI, nightly ingest, monthly release

---

## Key documents

- [Design](design.md) — technical architecture and data model
- [Tasks](tasks.md) — implementation phases and progress
- [Performance](performance.md) — market traction and analytics log
