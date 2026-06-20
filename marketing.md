# TickerTruth Marketing Plan
## Goal: Drive awareness, trial, and paid subscriptions for www.tickertruth.com

---

## 1. Target Audience

### Primary — the buyers

| Persona | Who they are | Pain point | Where to find them |
|---|---|---|---|
| **Quant Researcher** | Works at a prop desk, hedge fund, or systematic AIF. Builds backtests in Python/R. | Historical series are split-unadjusted. Mergers and delistings break price continuity. | LinkedIn, QuantLib India, GitHub |
| **Fintech Data Engineer** | Builds financial data pipelines at a fintech or neo-broker. | Corporate actions arrive late, de-normalized, or wrong from vendors. | LinkedIn, Discord |
| **Research Analyst (Broker side)** | Builds sector models or event studies at a brokerage. | NSE bulk-deal and corporate-action data needs manual cleanup before every analysis. | LinkedIn, BSE/NSE analyst groups |
| **Algo Trader / Indie Quant** | Self-funded, builds systematic strategies on NSE. | Suffers survivorship bias because data providers quietly drop dead tickers. | Reddit (r/IndiaInvestments, r/algotrading), Discord |
| **Head of Data / CTO at Fintech** | Budget holder at a Series A–C fintech with a data team. | Evaluates buy vs. build on reference data; the team keeps re-solving the same cleanup problems. | LinkedIn |

### Secondary — amplifiers (do not pitch directly; engage authentically)

- Financial data community builders (e.g., QuantInsti, Zerodha Varsity contributors)
- Open-source finance maintainers (Backtrader, Zipline India forks, OpenBB)
- Finance/ML newsletter writers on Substack or LinkedIn

---

## 2. Core Messaging

### Headline
**India equity data you can actually trust — symbol history, corporate actions, adjustment factors, versioned monthly.**

### Three proof-of-pain hooks (use these across all content)
1. **"Why your India backtest is probably lying to you"** — broken ticker continuity after mergers, demergers, and name changes
2. **"Corporate actions are not just dividends and splits"** — rights issues, buybacks, face-value changes, capital reductions that most teams miss
3. **"Survivorship bias is silent and expensive"** — delisted stocks quietly vanish from data feeds; TickerTruth tracks the graveyard

### Positioning statement (internal, use to guide all copy)
> TickerTruth is a versioned reference-data product for NSE equities — not raw price data, but the trust layer underneath it: symbol lineage, corporate action events, and split-adjusted factors, released monthly with a full changelog.

---

## 3. Platform Strategy

### 3.1 LinkedIn — primary channel for B2B buyers

**Audience:** Quant researchers, fintech data leads, algo traders in India  
**Tone:** Technical, first-person, problem-led. Show the data. Avoid hype.  
**Goal:** 2 posts/week; DM outreach 10 prospects/week; grow to 500 targeted followers in 90 days

**Content mix:**
- 50% educational (the "why it breaks" posts)
- 30% product/data updates (release highlights, sample queries)
- 20% social proof / community (dataset usage, interesting findings)

---

### 3.2 GitHub — credibility and discoverability

**Audience:** Data engineers, quants who evaluate vendor trustworthiness via code  
**Goal:** Strong README with methodology summary, sample notebooks, and a link to the dataset. Star count is social proof.

---

### 3.3 Hugging Face — passive inbound from the ML/data science community

**Audience:** ML practitioners who need financial data, data scientists building India market models  
**Goal:** Well-described dataset card, sample usage notebooks, link to TickerTruth for full access

---

### 3.4 Reddit — community engagement (not direct selling)

**Subreddits:** r/algotrading, r/IndiaInvestments, r/quant, r/dataisbeautiful  
**Tone:** Helpful community member. Share findings, not product pitches. Add value in comments.  
**Goal:** 1 post/week max; respond to questions where TickerTruth data is directly relevant

---

### 3.5 Direct outreach — highest conversion channel

**Target list:** Heads of data / quant team leads at India-focused AMCs, AIFs, fintech firms  
**Channels:** LinkedIn DM, cold email  
**Goal:** 10 outreaches/week; 3 design-partner conversations per month

---

## 4. Content Calendar — Weeks 1–12

> Week numbers are relative to campaign launch. Content for each post is drafted in Section 5.

### Week 1 — Foundation

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 1:** "Why India backtests break" — the symbol continuity problem |
| Wed | GitHub | Polish README with methodology summary and link to tickertruth.com |
| Thu | Hugging Face | Update dataset card with use-case description and sample notebook |

### Week 2 — First Product Signal

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 2:** "Corporate actions are not just dividends and splits" |
| Tue | Direct outreach | Batch 1: 10 DMs to quant leads and fintech data heads |
| Fri | LinkedIn | Share the Hugging Face dataset with a short product context post |

### Week 3 — Community Seeding

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 3:** "Survivorship bias in India equity data — the graveyard problem" |
| Tue | Direct outreach | Batch 2: 10 DMs |
| Wed | Reddit | Post in r/algotrading: share the "broken backtest" problem as a community question/finding |

### Week 4 — Sample Release + Pricing Reveal

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 4:** Product post — "TickerTruth first public release: what's in it" |
| Tue | Direct outreach | Batch 3: 10 DMs, mention first release |
| Thu | LinkedIn | Share release notes link (tickertruth.com/release-notes) as a product update post |

### Week 5 — Technical Depth

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 5:** Sample query walkthrough — "How to join symbol lineage to your price series in 5 lines of pandas" |
| Wed | GitHub | Publish sample notebook: `adjusted_vs_raw_series.ipynb` |
| Fri | LinkedIn | Share notebook snippet with chart: "Adjusted vs raw price after a bonus issue — the gap that breaks your backtest" |

### Week 6 — Social Proof / Design Partner Mention

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 6:** "What a design-partner review taught us about India corporate action data gaps" |
| Tue | Direct outreach | Batch 4: 10 DMs, reference design-partner program |
| Thu | Reddit | Reply in r/IndiaInvestments threads about backtesting tools |
| Fri | LinkedIn | Post the pricing page link with a context post explaining the tier rationale |

### Week 7 — Educational Series Continues

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 7:** "Rights issues, face-value changes, and capital reductions — the corporate actions your data vendor quietly ignores" |
| Wed | LinkedIn | Poll: "What's the biggest pain with India historical data? (split adjustment / delistings / mergers / corporate actions)" |
| Fri | LinkedIn | Share poll results with commentary |

### Week 8 — Release Notes Highlight

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 8:** "Monthly release is out — here's what changed in the NSE security master this month" |
| Tue | Direct outreach | Batch 5: 10 DMs to second-tier list (broker research teams, consultants) |
| Thu | Hugging Face | Update dataset with latest monthly snapshot and notify in model card |

### Week 9 — Use-Case Spotlights

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 9:** "Event-study methodology using correct corporate action dates — a before/after example" |
| Wed | GitHub | Publish second notebook: `action_event_examples.ipynb` |
| Fri | LinkedIn | Share the notebook with a striking chart |

### Week 10 — Pain Amplification

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 10:** "The hidden cost of bad reference data — a back-of-envelope calculation" |
| Tue | Direct outreach | Batch 6: 10 DMs focused on AMCs and AIF quant leads |
| Thu | Reddit | Post in r/quant: "Reference data quality for India equities — anyone solving this?" |

### Week 11 — Community & Comparison

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 11:** "NSE data sources compared: what each gives you and what each misses" |
| Fri | LinkedIn | Engage and reply to all comments on Post 11 (comparison posts drive discussion) |

### Week 12 — Momentum Review + Next Quarter Tease

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 12:** "12 weeks of TickerTruth — what we've shipped and what's next" |
| Thu | Direct outreach | Batch 7: Follow up on all warm leads from weeks 1–11 |
| Fri | LinkedIn | "Q2 roadmap: what's coming to TickerTruth" |

---

## 5. Content — Full Drafts

### Post 1 — LinkedIn
**"Why your India backtest is probably lying to you"**

---

> If you've ever run a backtest on NSE data and seen returns that looked too good, one likely culprit is symbol discontinuity.
>
> Here's what happens: a company undergoes a merger, a demerger, or a name change. The ticker changes. Most data vendors start a new series. The old series either disappears or stays orphaned.
>
> Your strategy looks like it traded a company that no longer exists, using a series that stopped being that company years ago.
>
> Three cases where this silently breaks your analysis:
> — HDFC Bank absorbed HDFC Ltd in 2023. Two tickers. One merged entity. Most vendors don't map the lineage.
> — Demergers create new tickers. The parent drops in price at demerger. Naïve backtests misread this as a loss.
> — Bonus issues and face-value changes shift the price series discontinuously. Unadjusted data makes it look like a crash.
>
> We built TickerTruth to fix this. It's a versioned reference-data layer for NSE equities: symbol lineage, corporate action events, and adjustment factors — released monthly with a full changelog.
>
> Free sample dataset at the link. Full access from INR 15,000/month.
>
> [tickertruth.com]

**Hashtags:** #QuantFinance #AlgoTrading #IndiaMarkets #DataEngineering #NSE #Backtesting

---

### Post 2 — LinkedIn
**"Corporate actions are not just dividends and splits"**

---

> Most financial data vendors track two corporate action types cleanly: cash dividends and stock splits.
>
> That's maybe 40% of the problem.
>
> What they routinely miss or mislabel for India equities:
>
> — Rights issues (price-adjusting, not just dilutive)
> — Bonus issues (NOT the same as a stock split, but treated identically by many vendors)
> — Face-value changes (a split by another name — your price series breaks if this isn't tracked)
> — Capital reductions (share buyback + cancellation, affects per-share metrics)
> — Demerger spin-offs (parent price drops; child is a new entity — is it in your universe?)
> — Amalgamations and scheme-of-arrangements (ticker replaced; most vendors silently drop the old one)
>
> Each of these requires a different adjustment factor and a different lineage mapping.
>
> Getting one wrong can corrupt years of price history downstream.
>
> TickerTruth normalizes all of these into a single corporate action event table with action type, effective date, ex-date, and an adjustment factor — versioned monthly.
>
> Free sample: [tickertruth.com]

**Hashtags:** #CorporateActions #IndiaEquities #DataQuality #QuantFinance #NSE

---

### Post 3 — LinkedIn
**"Survivorship bias in India equity data — the graveyard problem"**

---

> A commonly cited stat: most stock market indices look better than average because losers get removed.
>
> The same problem exists in your data feed, and it's worse than you think.
>
> When a company delists — voluntary delisting, regulatory action, merger, or NCLT — most vendors either drop the ticker entirely or stop updating it with no end-date.
>
> What this means for your analysis:
> — Universe construction: your "all NSE equities" screen misses the dead ones
> — Factor backtests: the stocks that went to zero aren't in your universe, so your model looks better
> — Event studies: delisting announcements are powerful alpha signals — but only if you have them
>
> TickerTruth maintains a full listing status history for NSE equities — active, suspended, delisted, and merged — with the effective date of each status change.
>
> The graveyard is part of the product.
>
> [tickertruth.com]

**Hashtags:** #SurvivorshipBias #NSE #QuantFinance #AlgoTrading #IndiaMarkets

---

### Post 4 — LinkedIn
**"TickerTruth first public release — what's in it"**

---

> Today we're publishing our first monthly data release at tickertruth.com.
>
> What's in the public sample:
> — NSE security master: current active securities with exchange metadata
> — Symbol alias table: name changes and ticker renames since 2010
> — Sample corporate action events: 30-day window of bonus, dividend, and rights events
> — Sample adjustment factors: split and bonus factors for a subset of large-caps
>
> What's in the paid release (Starter tier, INR 15,000/month):
> — Full historical lineage from 2000
> — Full corporate action event table (all action types, all years)
> — Backtest-ready adjustment factor map
> — Listing status history including delistings and mergers
> — Monthly release + changelog delivered to your inbox
>
> Full release notes: tickertruth.com/release-notes
> Pricing: tickertruth.com/pricing
>
> If you're working with NSE historical data and want to try the full dataset before committing, reply or DM me. We have 3 design-partner slots open.

**Hashtags:** #IndiaData #NSE #QuantFinance #DataProduct #OpenData

---

### Post 5 — LinkedIn
**"How to join symbol lineage to your price series in 5 lines of pandas"**

---

> The most common question we get: "How do I actually use the lineage table?"
>
> Here's the pattern:
>
> ```python
> import pandas as pd
>
> # Load TickerTruth tables
> lineage = pd.read_parquet("dim_symbol_alias.parquet")
> prices  = pd.read_parquet("fact_equity_eod.parquet")
>
> # Resolve all historical tickers to canonical entity ID
> prices_with_entity = prices.merge(
>     lineage[["symbol", "entity_id", "valid_from", "valid_to"]],
>     on="symbol", how="left"
> ).query("date >= valid_from and date < valid_to")
>
> # Now group by entity_id, not symbol — continuous series across renames
> continuous = prices_with_entity.groupby(["entity_id", "date"])["close"].last()
> ```
>
> That's the core pattern. Your backtest now tracks the entity, not the ticker string. Name changes, mergers, and renames don't break the series.
>
> Full sample notebook: [link to GitHub]
> Full dataset: tickertruth.com

**Hashtags:** #Python #Pandas #QuantFinance #NSE #DataEngineering

---

### Post 6 — LinkedIn
**"What a design-partner review taught us"**

---

> We gave early access to three teams building on NSE data. Here's what they found immediately:
>
> 1. **A quant fund discovered 40+ tickers in their universe that had merged or been renamed** — they had been running factor analysis on phantom companies for 18 months.
>
> 2. **A fintech data team found that their bonus issue adjustment logic was applying split ratios** — the two event types look similar but have different price adjustment formulas.
>
> 3. **A research analyst found that 12 corporate action events in their model were dated to the announcement date, not the ex-date** — each one was shifting a different day's alpha signal.
>
> None of these were edge cases. All three were live production issues.
>
> This is what TickerTruth is built to prevent. Clean event types, correct dates, explicit adjustment factors — versioned monthly.
>
> Design partner slots are now full, but we're onboarding Starter subscribers. tickertruth.com/pricing

**Hashtags:** #DataQuality #IndiaEquities #QuantFinance #NSE #ProductFeedback

---

### Post 7 — LinkedIn
**"The corporate actions your vendor quietly ignores"**

---

> In 10 years of India equity data, here's a rough count of corporate action types we've normalized for TickerTruth:
>
> ✓ Cash dividend
> ✓ Stock split (forward and reverse)
> ✓ Bonus issue
> ✓ Rights issue
> ✓ Face-value change
> ✓ Capital reduction / buyback + cancellation
> ✓ Demerger (parent record + child entity creation)
> ✓ Amalgamation / merger (target record closure + acquirer mapping)
> ✓ Scheme of arrangement
> ✓ NCLT-ordered restructuring
> ✓ Name change (no price impact, but breaks ticker continuity)
> ✓ ISIN change
>
> Most data vendors handle the first two cleanly. Some handle the next three. Very few handle everything below that.
>
> The ones at the bottom of the list are rare. But when they happen, they're catastrophic for any model using historical price or event data.
>
> Full taxonomy and methodology: tickertruth.com/methodology

**Hashtags:** #CorporateActions #NSE #DataEngineering #IndiaMarkets #QuantFinance

---

### Post 8 — LinkedIn (Monthly Release Post — template, update each month)
**"Monthly release is out — here's what changed"**

---

> TickerTruth June 2026 release is live at tickertruth.com/release-notes
>
> This month:
> — [X] securities in the master (updated from [Y] last month)
> — [N] corporate action events processed
> — [N] new adjustment factors computed
> — [N] symbol lineage events (renames, mergers, delistings)
>
> Notable this month:
> — [One specific interesting finding — e.g., "3 companies changed their face value this month, all in the SME segment"]
>
> Subscribers received the full release package by email.
>
> If you want next month's release, Starter tier is INR 15,000/month. tickertruth.com/pricing

**Hashtags:** #IndiaData #NSE #DataRelease #QuantFinance #CorporateActions

---

### Post 9 — LinkedIn
**"Event-study methodology using correct corporate action dates"**

---

> A common pattern in quant research: measure abnormal returns around a corporate event.
>
> The silent killer: most teams use the *announcement date* when they should use the *ex-date* (or record date). For some event types, these differ by weeks.
>
> Using the wrong date shifts your event window. Your cumulative abnormal return window is measuring the wrong period. The "alpha" you see is timing noise, not signal.
>
> TickerTruth provides both dates for every event: announced_date, ex_date, record_date, payment_date — whichever are available from NSE filings.
>
> Sample notebook showing the before/after difference on a bonus issue event study: [GitHub link]
>
> The difference in CAR[-5,+5] between announcement-date and ex-date alignment is often 3–4% on a typical bonus issue. That's not noise — it's a measurement error that corrupts your strategy.

**Hashtags:** #EventStudy #QuantFinance #NSE #CorporateActions #AlgoTrading

---

### Post 10 — LinkedIn
**"The hidden cost of bad reference data"**

---

> Back-of-envelope: how much does bad India reference data actually cost a quant team?
>
> Scenario: a 5-person quant team at a mid-sized AIF.
>
> — 1 analyst spends 3 days per quarter reconciling corporate action dates and adjustment factors: 12 days/year
> — 1 engineer spends 2 days per quarter cleaning symbol continuity issues in the data pipeline: 8 days/year
> — 1 strategy has 18 months of live history contaminated by survivorship bias (discovered in audit): backtest P&L was overstated by ~15%
>
> Conservative cost: 20 person-days of senior talent + an overfit strategy that underperformed its backtest.
>
> The reference data problem is not a data problem. It's an engineering and research reliability problem.
>
> TickerTruth Starter: INR 15,000/month. Less than one day of that analyst's time. tickertruth.com/pricing

**Hashtags:** #DataQuality #QuantFinance #CostOfBadData #IndiaEquities #NSE

---

### Post 11 — LinkedIn
**"NSE data sources compared: what each gives you and what each misses"**

---

> A quick map of where teams currently get NSE reference data, and the gaps each leaves:
>
> **NSE direct downloads (bhavcopy, corporate actions page)**
> ✓ Authoritative source
> ✗ No history for corporate actions older than 1–2 years
> ✗ No adjustment factors
> ✗ No symbol lineage or merge mapping
> ✗ Raw, unnormalized — every data type in a different format
>
> **Bloomberg / Refinitiv**
> ✓ Coverage is good for large-caps
> ✗ Expensive (often $20k–$100k/year)
> ✗ Corporate action taxonomy differs from NSE; India edge cases are often wrong
> ✗ No changelog — silent corrections with no audit trail
>
> **Free open datasets (Yahoo Finance, other scrapers)**
> ✓ Free
> ✗ No corporate action events, only price adjustments (no explanation)
> ✗ No lineage — dead tickers just disappear
> ✗ No versioning — last week's data may be silently different from today's
>
> **TickerTruth**
> ✓ Full lineage and corporate action taxonomy
> ✓ Adjustment factors with event provenance
> ✓ Versioned monthly with a full changelog
> ✓ INR-priced, India-focused
> ✗ Monthly cadence (not real-time)
> ✗ NSE-only in V1
>
> We're not the right fit for real-time feeds. We are the right fit for the reference layer underneath your analytics.
>
> tickertruth.com

**Hashtags:** #IndiaData #NSE #DataVendor #QuantFinance #DataEngineering

---

### Direct Outreach DM — Template A (LinkedIn, cold)

> Hi [Name], I noticed you're working on [quant/data engineering/analytics] at [Company] — looks like you're solving problems in the India equity space.
>
> We just launched TickerTruth (tickertruth.com) — a versioned reference-data layer for NSE equities covering symbol lineage, corporate action events, and adjustment factors. Monthly release with a full changelog.
>
> The main pain we solve: broken ticker continuity after mergers/renames, missing corporate action types (beyond dividends and splits), and survivorship bias from delisted tickers quietly disappearing.
>
> Would it be worth a 20-minute call to see if this is useful for your team? Happy to send a free sample first.

---

### Direct Outreach DM — Template B (Design partner)

> Hi [Name], I'm building TickerTruth — a reference-data product for NSE equities focused on symbol lineage, corporate actions, and adjustment factors.
>
> We're in an early design-partner phase and have one slot open. Design partners get full access at no cost for 3 months in exchange for an hour of feedback.
>
> Your work on [specific project/role] looks directly relevant. Would you be open to a quick chat?

---

## 6. Weekly Rhythm — Ongoing (After Week 12)

| Cadence | Action |
|---|---|
| Every Monday | Publish 1 LinkedIn post (rotate through educational, product update, use-case) |
| Every Tuesday | 10 direct outreach DMs |
| Monthly (on release day) | LinkedIn release post + Hugging Face dataset update + subscriber email |
| Monthly | 1 sample notebook or walkthrough published to GitHub |
| Quarterly | Review: follower growth, inbound leads, conversion from outreach |

---

## 7. Success Metrics — 90-Day Targets

| Metric | Target |
|---|---|
| LinkedIn followers (net new, targeted) | 300–500 |
| LinkedIn post impressions (avg per post) | 1,000+ |
| Hugging Face dataset downloads | 200+ |
| Direct outreach conversations started | 50+ |
| Design partner conversations | 5–8 |
| Paid conversions | 1–3 |
| Website unique visitors/month by week 12 | 500+ |

---

## 8. Tools Needed

| Tool | Purpose | Cost |
|---|---|---|
| LinkedIn personal profile | All B2B content and DMs | Free |
| GitHub (existing) | Credibility, notebooks, README | Free |
| Hugging Face (existing) | Passive discovery and sample distribution | Free |
| Canva or similar | Simple charts for LinkedIn posts | Free tier |
| Notion or Airtable | Track outreach leads and status | Free tier |
| Substack (optional, later) | Email newsletter for warm leads who aren't ready to buy | Free |

---

## 9. Red Lines (What Not to Do)

- Do not cold-spam LinkedIn connections without a personalized hook
- Do not pitch in Reddit comments — add value first, link only when directly relevant
- Do not claim real-time data coverage — TickerTruth is a monthly reference product
- Do not compare directly to Bloomberg/Refinitiv on price or scale — compete on India-specificity and transparency
