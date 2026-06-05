---
license: cc-by-4.0
language:
  - en
tags:
  - finance
  - india
  - nse
  - equities
  - reference-data
  - isin
  - symbol-master
pretty_name: "TickerTruth — NSE India Security Master (Explorer)"
thumbnail: https://huggingface.co/datasets/tickertruth/nse-india-security-master/resolve/main/images/tickertruth_favicon.png
size_categories:
  - 1K<n<10K
task_categories:
  - other
---

# TickerTruth — NSE India Security Master (Explorer)

A clean, normalized reference table of **2,389 NSE-listed equities** — ISIN mappings, listing dates, company names, and active/delisted status — built from the [TickerTruth](https://tickertruth.com) India reference-data pipeline.

## Why this dataset exists

India equity data is notoriously messy. NSE symbols change (renames, mergers, delistings), ISINs get reissued, and raw bhavcopy files carry no historical context. TickerTruth's pipeline normalizes the NSE equity master daily and tracks these changes. This dataset is the starting point — a clean security master you can trust as a join key.

## Files

| File | Rows | Description |
|---|---|---|
| `data/nse_security_master.csv` | 2,389 | All active NSE-listed equities as of June 2026 |
| `data/nse_explorer_20symbols.csv` | 20 | Explorer slice — 20 blue-chip NIFTY50 stocks for trial use |

## Schema

| Column | Type | Description |
|---|---|---|
| `nse_symbol` | string | NSE trading symbol (e.g. `RELIANCE`) |
| `isin` | string | 12-character ISIN — stable cross-reference key |
| `company_name` | string | Full registered company name |
| `listing_date` | date (YYYY-MM-DD) | Date first listed on NSE |
| `active_flag` | boolean | `True` = currently trading; `False` = delisted/suspended |

## Explorer symbols (20-stock slice)

The `nse_explorer_20symbols.csv` file covers the 20 most liquid NIFTY50 constituents:

`ASIANPAINT` · `AXISBANK` · `BAJFINANCE` · `BHARTIARTL` · `HCLTECH` · `HDFCBANK` · `HINDUNILVR` · `ICICIBANK` · `INFY` · `KOTAKBANK` · `LT` · `MARUTI` · `NTPC` · `ONGC` · `RELIANCE` · `SBIN` · `SUNPHARMA` · `TCS` · `TITAN` · `WIPRO`

## Usage

```python
import pandas as pd

# Full security master
master = pd.read_csv("data/nse_security_master.csv", parse_dates=["listing_date"])

# Look up by ISIN
master.set_index("isin").loc["INE002A01018"]  # RELIANCE

# Filter active only
active = master[master["active_flag"]]
print(f"{len(active)} active NSE equities")

# Explorer slice
explorer = pd.read_csv("data/nse_explorer_20symbols.csv", parse_dates=["listing_date"])
```

Or load directly from Hugging Face:

```python
from datasets import load_dataset

ds = load_dataset("tickertruth/nse-india-security-master", data_files="data/nse_security_master.csv")
df = ds["train"].to_pandas()
```

## Data source and pipeline

Raw data is fetched nightly from the NSE public equity master. The pipeline:

1. Downloads the NSE equity master CSV
2. Deduplicates and normalizes company names, ISINs, and listing dates
3. Runs quality checks (ISIN format validation, duplicate detection, confidence scoring)
4. Writes the curated output — what you see here

Source: NSE India public archives (equity master)
Pipeline: [github.com/brkrishna/TickerTruth](https://github.com/brkrishna/TickerTruth)

## What's coming

This initial release covers the security master only. Subsequent releases will add:

- **Symbol lineage events** — rename, delisting, merger, and re-listing events with effective dates (the pipeline tracks daily snapshots and will surface changes as they occur)
- **Corporate actions** — dividends, splits, bonus issues, rights offerings
- **Adjustment factors** — back-adjusted price multipliers for each corporate action

Updates publish nightly. Watch or star the dataset to be notified.

## License

CC BY 4.0 — free to use, share, and adapt with attribution.

> Source: NSE India public equity master, normalized by TickerTruth.  
> Pipeline: https://github.com/brkrishna/TickerTruth

## Citation

```bibtex
@dataset{tickertruth_nse_2026,
  title   = {TickerTruth NSE India Security Master},
  author  = {TickerTruth},
  year    = {2026},
  url     = {https://huggingface.co/datasets/tickertruth/nse-india-security-master},
  license = {CC-BY-4.0}
}
```
