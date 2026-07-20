---
title: "Welcome to the TickerTruth Blog"
date: 2026-07-20
description: "Why we're writing about India equity reference data — symbol lineage, corporate actions, and the broken-backtest problem."
tags: ["announcements"]
---

TickerTruth started from a narrow, specific frustration: backtests on Indian equities that quietly fall apart because a ticker was reused, a symbol was renamed without anyone updating the mapping, or a bonus issue was applied on the wrong date. None of these show up as errors — they show up as *wrong numbers that look plausible*, which is the worst kind of bug in a trading system.

This blog is where we'll write about the parts of that problem that don't fit in release notes:

- **Symbol lineage edge cases** — mergers, delistings, and the handful of NSE symbols that have been reused across genuinely unrelated companies over the last two decades.
- **Corporate action adjustment mechanics** — how split/bonus/rights ratios chain together, and where naive cumulative-factor math breaks.
- **Data quality tradeoffs** — why we'd rather flag a record `LOW` confidence than silently drop it, and what that means for anyone consuming the reference tables.
- **Pipeline and release engineering** — the boring-but-load-bearing details of running a monthly versioned data release without breaking downstream consumers.

If you're backtesting strategies on NSE or BSE history and you've ever had a Sharpe ratio that seemed too good to be true, there's a decent chance a corporate action adjustment — or a silent symbol swap — is why. That's the layer we're trying to make boring and correct.

Posts here will be short and specific: one problem, one worked example, one takeaway. Subscribe via [RSS](/blog/index.xml) if you want new posts as they land, or check the [methodology](/methodology.html) page for how the underlying pipeline works end to end.
