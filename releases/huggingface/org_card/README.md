---
title: TickerTruth
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: static
pinned: false
---

# TickerTruth

Reference data for Indian equity markets — versioned, normalized, and production-ready.

We build the trust layer that Indian equity analytics is missing: clean symbol histories, corporate action events, and adjustment factors for NSE-listed securities.

---

## What we publish

| Dataset | Description |
|---|---|
| [nse-india-security-master](https://huggingface.co/datasets/tickertruthorg/nse-india-security-master) | NSE security master — ISIN mappings, listing dates, active/delisted status. Updated nightly. |

More datasets coming: symbol lineage events, corporate actions, and pre-computed adjustment factors.

## Interactive Explorer

Browse and filter the data without writing any code: [tickertruth-nse-explorer](https://huggingface.co/spaces/tickertruth/tickertruth-nse-explorer)

---

## The problem we solve

Backtesting Indian equities breaks silently. Symbols rename without warning, splits go unapplied, and historical corporate action records are scattered across inconsistent sources. TickerTruth normalizes all of this into a consistent, versioned schema so your pipeline doesn't have to.

---

## Links

- Site: [tickertruth.com](https://tickertruth.com)
- Explorer: [tickertruth-nse-explorer](https://huggingface.co/spaces/tickertruth/tickertruth-nse-explorer)
- Pipeline: [github.com/brkrishna/TickerTruth](https://github.com/brkrishna/TickerTruth)
- License: CC BY 4.0 (free tier) — see dataset card for details
