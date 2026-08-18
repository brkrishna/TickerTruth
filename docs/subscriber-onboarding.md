# You're Subscribed — Here's How to Access Your Data

Welcome to TickerTruth. This page covers everything you need for your first
release: what's in the bundle, how to load it, and what to expect going
forward.

---

## 1. What's in Your Bundle

You'll receive a `tickertruth_starter_{date}.zip` by email as a signed R2
download link (expires in 7 days). Inside:

| File | Format | What it is |
|---|---|---|
| `nse_active_securities_sample_{date}.csv` | CSV | Public sample of active NSE securities |
| `corporate_actions_sample_{date}.csv` | CSV | Public sample of recent corporate action events |
| `extended_nse_master_{date}.csv` | CSV | Full security master (up to 1,000 securities) — `security_id`, `nse_symbol`, `isin`, `company_name`, `issuer_id`, `exchange_id`, `listing_date`, `active_flag` |
| `corporate_actions_3yr_{date}.parquet` | Parquet | Corporate action events, last 3 years — `security_id`, `action_code`, `event_date`, `record_date`, `payment_date`, `old_value`, `new_value`, `adjustment_factor`, `confidence_score`, `confidence_flag` |
| `adjustment_factors_{date}.parquet` | Parquet | Cumulative split/bonus/dividend adjustment factors — `security_id`, `as_of_date`, `cumulative_split_adjustment`, `cumulative_bonus_adjustment`, `cumulative_dividend_adjustment`, `total_adjustment_factor` |
| `MANIFEST.json` | JSON | Checksums and row counts for every file in the bundle |
| `LICENSE.md` | Markdown | Usage terms for your tier |

Symbol lineage (`fact_symbol_lineage_event`) is a Professional/Enterprise-tier
file, not included in Starter. If you need it, reply to this email and we'll
talk about upgrading.

**Before using anything else, verify the download:**

```bash
sha256sum tickertruth_starter_{date}.zip
# Compare against the checksum for this file in MANIFEST.json
```

---

## 2. Loading Each File

```python
import pandas as pd

securities = pd.read_csv("extended_nse_master_{date}.csv")
actions    = pd.read_parquet("corporate_actions_3yr_{date}.parquet")
factors    = pd.read_parquet("adjustment_factors_{date}.parquet")
```

---

## 3. Applying Adjustment Factors to a Price Series

```python
prices_adjusted = (
    prices.merge(factors, on="security_id", how="left")
          .assign(adjusted_close=lambda d: d["close"] * d["total_adjustment_factor"])
)
```

`total_adjustment_factor` is cumulative as of `as_of_date` — join on the
nearest prior `as_of_date` per `security_id` if your price series spans
multiple adjustment events.

---

## 4. Release Schedule

New releases ship on the **first business day of each month**, with a full
changelog at [tickertruth.com/release-notes](https://tickertruth.com/release-notes).
You'll get a renewal email each month with a fresh signed download link —
no action needed on your end unless you want to change tiers.

---

## 5. Support

Questions, data issues, or link problems: **contact@tickertruth.com**.
We reply within 24 hours.

---

## 6. 30-Day Money-Back Guarantee

If TickerTruth isn't useful for your pipeline in the first 30 days, tell us
and we'll refund your first payment in full — no questions asked. Email
contact@tickertruth.com to request it.
