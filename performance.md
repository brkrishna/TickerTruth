# TickerTruth — Market Performance Tracker

Tracks traction, reach, and product-market signal over time. Updated on the cadence below.

---

## Metrics collection cadence

| Metric | Source | Frequency | How to collect |
|---|---|---|---|
| Web traffic (visits, unique visitors, top pages) | Cloudflare Web Analytics | Weekly (Monday) | Cloudflare dashboard → Analytics → Web Analytics → export or screenshot |
| Core Web Vitals (LCP P50/P75/P90) | Cloudflare Web Analytics | Monthly | Same dashboard, filter by month |
| LinkedIn impressions, reach, engagements | LinkedIn Page Analytics | Weekly (Monday) | LinkedIn → Analytics → Export CSV (select prior week) |
| LinkedIn followers | LinkedIn Page Analytics | Weekly (Monday) | Same export |
| LinkedIn post performance | LinkedIn → Top Posts tab | Per post, within 7 days of publish | Note impressions + engagement rate manually |
| GitHub stars / forks / traffic | GitHub Insights | Weekly (Monday) | GitHub repo → Insights → Traffic |
| Email / DM leads | Manual | As they arrive | Log in the Leads table below |
| Paid conversions | Manual | As they arrive | Log in the Conversions table below |

---

## Tasks: recurring analytics workflow

- [ ] **Every Monday** — pull LinkedIn CSV export for the prior week; add a new entry to the Weekly LinkedIn Snapshot table below
- [ ] **Every Monday** — note Cloudflare web visits and unique visitors for the prior week
- [ ] **Every Monday** — check GitHub repo traffic (Insights → Traffic) and note stars delta
- [ ] **After each LinkedIn post** — record the post URL, publish date, and 7-day impressions/engagements in the Post Performance Log below
- [ ] **Monthly (first Monday of month)** — capture Core Web Vitals from Cloudflare and note P75 LCP; flag if > 2,500ms
- [ ] **Monthly** — update the Conversion Funnel with cumulative lead and buyer counts

---

## Analytics log

Entries are added newest-first. Each entry is a timestamped snapshot.

---

### 2026-06-17 — Week 1 baseline

**Period:** 2026-06-11 → 2026-06-17  
**Captured:** 2026-06-17

#### Web analytics (Cloudflare) — May 18 → Jun 17 2026

| Metric | Value | Notes |
|---|---|---|
| LCP P50 | 380ms | Excellent |
| LCP P75 | 1,472ms | Needs improvement |
| LCP P90 | 4,556ms | Poor — investigate slow-loading pages |
| LCP P99 | 4,556ms | Same as P90, likely single outlier URL |
| Pages tracked | tickertruth.com/, tickertruth.com/release-notes | |
| Bot traffic | Excluded | |

Action: P90/P99 LCP of 4.5s is too slow. Investigate which asset on `tickertruth.com/` and `/release-notes` is the bottleneck. Target P75 < 2,500ms.

#### LinkedIn analytics — 2026-06-11 → 2026-06-17

| Metric | Value |
|---|---|
| Impressions | 32 |
| Members reached | 26 |
| Engagements | 0 |
| New followers | 1 (gained 2026-06-16) |
| Total followers | 1 |

#### LinkedIn post performance

| Post | Publish date | Impressions | Engagements | Engagement rate |
|---|---|---|---|---|
| #tickertruth #india corporate-actions symbol … | 2026-06-15 | 32 | 0 | 0% |

**Post URL:** [View post](https://www.linkedin.com/posts/ticker-truth-359407416_tickertruth-india-corporate-actions-symbol-share-7472249403903463424-Xx5G)

#### Leads & conversions

| Date | Source | Type | Notes |
|---|---|---|---|
| — | — | — | None yet — week 1 |

#### Week 1 summary

First post published 2026-06-15. 32 impressions, 26 unique members reached, 0 engagements, 1 follower. No web traffic data yet at page-visit granularity (Cloudflare beacon-based analytics; may take a few days to populate visit counts). Baseline established. Engagement rate of 0% is expected for a brand-new page with 1 follower — the metric to watch next week is whether the "Why India backtests break" post (Wednesday 2026-06-18) drives click-throughs to tickertruth.com.

---

## Conversion funnel (cumulative)

| Stage | Count | Last updated |
|---|---|---|
| LinkedIn followers | 1 | 2026-06-17 |
| Website visits (unique) | — | 2026-06-17 (no data yet) |
| GitHub stars | — | collect 2026-06-23 |
| Email / DM leads | 0 | 2026-06-17 |
| Paid conversions | 0 | 2026-06-17 |

---

## Post performance log

| # | Platform | Title / topic | Publish date | 7-day impressions | 7-day engagements | Link |
|---|---|---|---|---|---|---|
| 1 | LinkedIn | Why India backtests break — symbol continuity problem | 2026-06-15 | 32 | 0 | [link](https://www.linkedin.com/posts/ticker-truth-359407416_tickertruth-india-corporate-actions-symbol-share-7472249403903463424-Xx5G) |
| 2 | GitHub | README polish + methodology summary | 2026-06-18 | — | — | — |

---

## Notes on interpreting early metrics

- Impressions without engagements (0%) is normal at < 50 followers. Focus on impressions growth week-over-week, not engagement rate.
- Cloudflare Web Analytics uses a JS beacon, not server logs. First-party, privacy-preserving — counts may be slightly lower than server-side tools.
- GitHub traffic (Insights) only shows 14-day windows. Snapshot it weekly or you lose the data.
- A single DM from a quant or portfolio manager outweighs 1,000 passive impressions — log leads even if they don't convert.
