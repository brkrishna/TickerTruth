# ICASHTL — NSE Symbol History & Corporate Actions

**Tier:** Starter
**Release date:** 2026-06-01

## Contents

- `data/extended_nse_master_20260601.csv`
- `data/nse_active_securities_sample_20260601.csv`
- `LICENSE.md` — usage terms
- `sample_queries.sql` — example SQL queries
- `MANIFEST.json` — checksums and metadata

## Key columns

| Column | Description |
|---|---|
| `nse_symbol` | NSE trading symbol (normalised, no series suffix) |
| `isin` | 12-character ISIN — stable identifier across renames |
| `action_code` | Corporate action type (SPLIT, BONUS, DIVIDEND, …) |
| `event_date` | Ex-date for corporate actions |
| `total_adjustment_factor` | Cumulative price multiplier for backtesting |
| `confidence_score` | 0.0–1.0 data quality score |

## Verification

```bash
# Verify file integrity (Linux/macOS)
sha256sum -c MANIFEST.json  # or check manually against MANIFEST.json
```

## Support

contact@icashtl.com — include your buyer ID and tier in subject line.
