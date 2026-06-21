# TickerTruth Marketing Plan
## Goal: First paying customer within 4 weeks

---

## 0. Blockers to fix before any outreach (Day 1–2 tasks)

These are not marketing tasks — they are revenue blockers. If someone says "yes" today, you cannot close them.

| Blocker | Fix | Owner | ETA |
|---|---|---|---|
| No payment collection | Set up Razorpay (India) + Stripe (international). INR invoicing + UPI for domestic, card for international. Takes ~1 day. | — | Day 1 |
| No subscriber delivery model | Pick **R2 presigned links delivered by email** as the MVP. Skip the portal. One email with a signed URL per release. Takes 2 hours. | — | Day 1 |
| No onboarding checklist | Write a 1-page "You're subscribed — here's how to access your data" doc. | — | Day 2 |
| No pricing page CTA | Add a "Buy now" button on tickertruth.com/pricing that links to a Razorpay payment link or a Calendly for a 20-min call. | — | Day 2 |

**Do not send outreach until these are done.** Getting a yes and then stumbling on payment kills the deal.

---

## 1. First Customer Sprint — 4-Week Plan

The goal of weeks 1–4 is exactly one thing: one paying customer. Everything else is secondary.

### The conversion path
```
Outreach DM / email
       ↓
20-min demo call (Calendly)
       ↓
Free 7-day data sample sent immediately
       ↓
Follow-up call, 48 hours later
       ↓
Payment link (Razorpay / Stripe)
```

No long design-partner programs. No 3-month free access. A 7-day sample is enough to validate the product. If they need more, offer a 30-day money-back guarantee instead.

### Sprint calendar

| Day | Action | Volume |
|---|---|---|
| 1–2 | Fix blockers (Section 0) + build target list (Section 2) | — |
| 3 | Launch LinkedIn post 1 ("Why your India backtest is lying to you") | 1 post |
| 3 | Start outreach batch 1: top 20 from target list | 20 DMs |
| 4–5 | Follow up on batch 1 non-replies; send free sample to everyone who responds | — |
| 7 | LinkedIn post 2 ("Corporate actions are not just dividends and splits") | 1 post |
| 7 | Outreach batch 2: next 25 from target list | 25 DMs |
| 10 | Share 5-minute Loom demo on LinkedIn | 1 video post |
| 10 | Follow up on all week-1 outreach that hasn't responded (second touch) | — |
| 14 | LinkedIn post 3 ("Survivorship bias — the graveyard problem") | 1 post |
| 14 | Outreach batch 3: 25 more + any warm referrals | 25 DMs |
| 15 | Third touch: final follow-up on week-1 non-replies with specific data hook | — |
| 18 | Post in India-specific communities (Section 6) | — |
| 21 | LinkedIn post 4 (product launch: "TickerTruth first public release") | 1 post |
| 21 | Outreach batch 4: 20 second-tier targets | 20 DMs |
| 28 | Review: calls booked, trials sent, payment conversations. Convert. | — |

**Minimum outreach to hit first customer: 90 personalized messages in 4 weeks (not 10/week).**

---

## 2. Target Company List — Specific

Build a named list in Notion/Airtable with contact name, LinkedIn URL, company, role, and status. Work this list every week.

### Tier 1 — Quant funds and AIFs (highest budget, highest pain, buy fast)

| Company | What they build | Why they need this |
|---|---|---|
| DSP Quant Fund | Systematic equity strategies | Adjustment factors and survivorship bias |
| Nippon India Quant | Factor models | Corporate action event dates |
| Edelweiss AIF (quant strategies) | Systematic long-short | Full lineage for merger/demerger events |
| Marcellus Investment Managers | Concentrated quality portfolios | ISIN-level historical continuity |
| Quantum AMC | Active quant | Correct ex-dates for event studies |
| Axis AMC (systematic) | Factor-based allocation | Symbol continuity across renames |
| Motilal Oswal AMC (quant) | Momentum strategies | Survivorship-free universe |
| White Oak Capital | Systematic AIF | Corporate action taxonomy |

**Who to contact at each:** Head of Research / Head of Quant / Head of Data Engineering. Find them on LinkedIn — search "[Company] quant" or "[Company] data".

### Tier 2 — Fintechs and algo platforms (growing teams, recurring pain in pipelines)

| Company | Persona | Pain point |
|---|---|---|
| Smallcase Technologies | Data engineers | Symbol continuity for strategy baskets |
| Streak (AlgoLab) | Product team | Adjustment factors for backtester accuracy |
| Sensibull | Quant/data | Underlying corporate action events |
| Dhan | Data engineering | Reference data for trading terminal |
| Fyers (Kite Connect API users) | Algo teams | Clean corporate action events |
| AlgoTest | Product | Survivorship-free universe for backtest |
| INDmoney | Data team | Corporate action taxonomy for portfolio tracking |

### Tier 3 — Broker research teams (volume users, slower buying cycle)

| Company | Persona |
|---|---|
| Kotak Securities Research | Quant analyst |
| ICICI Securities Research | Data engineer |
| Emkay Global | Quant researcher |
| Spark Capital | Research analyst |
| JM Financial | Equity research head |

### Tier 4 — Independent quants and consultants (fast to decide, lower ACV but easiest first sale)

- QuantInsti EPAT alumni who run their own algo funds
- Independent quant consultants on LinkedIn India
- Finance PhD/postdocs at IIMs, IITs working on India market research
- Freelance data engineers building NSE pipelines

**Target 5–10 from Tier 4 first** if Tiers 1–3 stall. They buy in 3 days, not 3 months. Lower ACV but a first paid customer breaks the psychological and social barrier.

---

## 3. Founding Customer Offer

Create urgency. Most people won't buy because they aren't sure it's worth it — not because they don't have the budget.

### Founding customer pricing

> **5 founding customer slots — INR 10,000/month (instead of INR 15,000/month), locked for 12 months.**  
> Access to Starter tier. Discount disappears when slots fill.

Use this in every outreach DM and LinkedIn post 4 onwards.

**Why this works:**
- Creates scarcity and urgency without devaluing the product long-term
- 12-month lock-in signals they're getting a real deal
- INR 10k/month is below the approval threshold at most Indian companies (no PO needed)
- 33% discount feels meaningful; the actual margin impact is small if you convert 5 customers

**Script for the urgency moment in calls:**
> "We have 5 founding customer slots at INR 10,000/month, locked for 12 months. Two are taken. I can hold one for you until [date 5 days out] if you want to think it over — after that it goes to the next person on the list."

---

## 4. Lead Magnet — Email Capture Before They're Ready to Buy

Most contacts won't be ready to buy on first touch. Capture their email with a free artifact they genuinely want.

### Lead magnet: "India Backtest Integrity Report"

A 6-page PDF + Google Colab notebook showing:
- How to audit your own price series for corporate action errors
- The 5 most common NSE data errors (with real examples)
- How survivorship bias inflates backtest Sharpe by ~0.3 on India small-cap strategies
- A checklist: "Is your India data pipeline clean?"

**Distribution:**
- Gate it with email address (use ConvertKit free tier or a simple Cloudflare Pages form → email)
- Link from every LinkedIn post, GitHub README, and Hugging Face dataset card
- Mention it in outreach DMs as a warm step: "I can send you our free audit report first if you want to see how we approach the problem"
- Everyone who downloads is a warm lead — follow up in 48 hours with a DM or email

**Build time:** 1 day (the notebooks already exist; it's a repackage + landing page form).

---

## 5. The 5-Minute Loom Demo — Single Highest-Value Asset

One 5-minute screen recording that shows:
1. Load a raw price series with a bonus issue — show the discontinuity
2. Join to TickerTruth adjustment factors — show the corrected series
3. Run the lineage join — show how a renamed ticker gets a continuous entity ID
4. Show the corporate action event table — highlight the action type and ex-date

**Where to use it:**
- LinkedIn post (day 10 of sprint)
- Attach to outreach follow-ups ("I made a short demo — might be easier than me explaining it")
- Embed on tickertruth.com homepage above the fold
- Pin to GitHub README

**Build time:** 2 hours. Record in one take. Rough is fine — roughness signals authenticity, not polish.

---

## 6. India-Specific Channels (Not in Original Plan)

These communities exist where your exact buyers spend time. Current plan doesn't use them.

### 6.1 QuantInsti (EPAT alumni network)
- ~50,000 alumni, many are active algo traders and quant fund managers
- Community forum at quantinsti.com + private Slack/Discord
- Post in their community: share the "broken backtest" educational post
- **Contact QuantInsti directly** — offer to write a guest blog post or deliver a free webinar on "India reference data quality." They accept these regularly. Webinar to 500 attendees > 500 LinkedIn posts.

### 6.2 NISM and BSE Institute
- NISM runs SEBI certification programs; alumni are compliance and research professionals
- BSE Institute has a finance community
- Less direct, but good for brand awareness among serious practitioners

### 6.3 CFA Society India / CMT Association India
- Monthly events in Mumbai, Delhi, Bangalore
- Submit a talk proposal: "Reference data quality in India equity backtesting" fits their content
- Attendees are exactly your Tier 1 buyer persona
- **Events take 4–8 weeks to schedule — start this week.**

### 6.4 Zerodha / Kite Connect ecosystem
- Kite Connect API has an active developer community (Zerodha Developers forum, TradingQ&A)
- Many indie algo traders use Kite Connect — they are your Tier 4 buyers
- Post a helpful technical answer in TradingQ&A threads about historical data gaps; don't pitch directly

### 6.5 Telegram / WhatsApp algo-trading groups
- Dozens of active Indian algo-trading Telegram groups (search "algo trading India Telegram")
- Post the free Loom demo or the backtest integrity report — value-first, not pitch
- Do not spam; join 2–3 groups and be a genuine participant for a week first

### 6.6 LinkedIn groups (underused in current plan)
- "Quant Finance India" (LinkedIn group)
- "Algorithmic Trading India"
- "FinTech India"
- Post the same educational content you'd post on your feed, but reach a different audience

### 6.7 Reddit — r/algotrading and r/IndiaInvestments
- Keep the current plan (1 post/week, value-first)
- Best post type: "I dug into NSE corporate action data quality and found X — here's what I found" with real data, no product pitch. Let people ask about the tool.

---

## 7. Outreach Templates — Updated for Urgency

### Template A — LinkedIn DM, cold (Tier 1/2 targets)

> Hi [Name], I saw you're [building quant strategies / leading data at] [Company].
>
> We just launched TickerTruth — a versioned reference-data layer for NSE (and BSE) equities: full symbol lineage, corporate action events with correct ex-dates, and split-adjusted factors. Monthly release with a changelog.
>
> Quick version of why it matters: most India data feeds either drop dead tickers silently or mislabel bonus issues as splits. If you run backtests on NSE data, your price series is probably wrong in at least 3–5 places per 100 symbols.
>
> Happy to send a free 7-day sample and a 5-min demo recording now — no call needed. If it's useful, we have a founding-customer slot at INR 10,000/month.
>
> Worth a look?

**What changed:** Shorter. Specific pain point up front. Free sample + demo, not a call. Urgency (founding customer slot). Clear ask.

---

### Template B — LinkedIn DM, warm (second touch, no reply after 4 days)

> Hi [Name], following up on my note from [day].
>
> Attaching one specific thing that might be relevant: in the last NSE data pull, we found [X] companies in the Nifty 500 that changed their ticker or underwent a corporate restructuring in the past 24 months — and most data vendors either have the wrong ticker or no lineage mapping at all.
>
> Happy to share the full list with you, no cost. If this kind of thing shows up in your pipeline, it's worth a 15-min call.

**What's different:** The second touch has a specific, personalized data hook — not just "following up." Give them something before asking for their time.

---

### Template C — LinkedIn DM, Tier 4 (indie quant, fast decision)

> Hi [Name], I noticed you're building [algo strategies / systematic approaches] on NSE data.
>
> Quick question: how are you handling split and bonus adjustments, and corporate action event dates in your backtest? Most indie setups I've seen use Yahoo Finance or NSE bhavcopy — both have significant gaps in adjustment accuracy.
>
> I built TickerTruth to fix this. Free sample + founding customer pricing (INR 10k/month) if you want to check it out.

**Why:** Indie quants respond to direct, peer-level language. No corporate formality.

---

### Template D — Cold email (for contacts where you can find a company email)

**Subject:** NSE reference data for [Company] — quick sample offer

> Hi [Name],
>
> I'm reaching out because [Company] is building in the India equity space and this might save your team real time.
>
> TickerTruth is a versioned reference-data product for NSE + BSE equities — symbol lineage (mergers, renames, delistings), corporate action events with correct ex-dates, and backward adjustment factors. Monthly release with a full changelog.
>
> If your team works with historical NSE data, I can send a free 7-day sample today. No strings — just want you to see if it's useful.
>
> Calendly for a 15-min call if you'd rather talk first: [link]
>
> Best,  
> [Name]  
> tickertruth.com

---

### Template E — Follow-up sequence (third touch, day 10)

> Hi [Name], last message from me on this.
>
> I've attached the "India Backtest Integrity Report" we published this week — it's a free audit framework for checking corporate action errors in your price series. Useful regardless of whether you use our data.
>
> If you do want to see TickerTruth before the founding-customer window closes, the link is tickertruth.com/pricing.
>
> Either way, good luck with [what they're building].

**Why:** Third touch gives value, creates a soft close on the founding-customer window, and exits gracefully. No fourth touch for 30 days.

---

## 8. Target Audience

### Primary — the buyers

| Persona | Who they are | Pain point | Where to find them |
|---|---|---|---|
| **Quant Researcher** | Works at a prop desk, hedge fund, or systematic AIF. Builds backtests in Python/R. | Historical series are split-unadjusted. Mergers and delistings break price continuity. | LinkedIn, QuantInsti alumni, CFA India |
| **Fintech Data Engineer** | Builds financial data pipelines at a fintech or neo-broker. | Corporate actions arrive late, de-normalized, or wrong from vendors. | LinkedIn, Zerodha Kite Connect community |
| **Algo Trader / Indie Quant** | Self-funded, builds systematic strategies on NSE. | Suffers survivorship bias because data providers quietly drop dead tickers. | Reddit, Telegram, QuantInsti alumni, TradingQ&A |
| **Research Analyst (Broker side)** | Builds sector models or event studies at a brokerage. | NSE corporate-action data needs manual cleanup before every analysis. | LinkedIn, Spark/Emkay/JM research teams |
| **Head of Data / CTO at Fintech** | Budget holder at a Series A–C fintech with a data team. | Team keeps re-solving the same cleanup problems. | LinkedIn |

### Secondary — amplifiers (engage authentically, no direct pitch)

- QuantInsti instructors and EPAT content team
- Finance/ML newsletter writers (Substack, LinkedIn)
- OpenBB, Backtrader, Zipline maintainers

---

## 9. Core Messaging

### Headline
**India equity data you can actually trust — symbol history, corporate actions, adjustment factors, versioned monthly.**

### Three proof-of-pain hooks
1. **"Why your India backtest is probably lying to you"** — broken ticker continuity after mergers, demergers, and name changes
2. **"Corporate actions are not just dividends and splits"** — rights issues, buybacks, face-value changes, capital reductions that most teams miss
3. **"Survivorship bias is silent and expensive"** — delisted stocks quietly vanish from data feeds; TickerTruth tracks the graveyard

### Positioning statement
> TickerTruth is a versioned reference-data product for NSE + BSE equities — not raw price data, but the trust layer underneath it: symbol lineage, corporate action events, and split-adjusted factors, released monthly with a full changelog.

---

## 10. Platform Strategy

### 10.1 LinkedIn — primary channel
**Audience:** Quant researchers, fintech data leads, algo traders in India  
**Tone:** Technical, first-person, problem-led. Show the data. Avoid hype.  
**Goal:** 3 posts/week (up from 2) in weeks 1–4; DM outreach 20–30/week

**Content mix:**
- 50% educational (the "why it breaks" posts)
- 30% product/data updates (release highlights, sample queries, demo video)
- 20% social proof / community findings

---

### 10.2 GitHub — credibility and discoverability
**Goal:** Strong README with methodology summary, sample notebooks, Colab badges, and link to tickertruth.com. Star count is social proof.

---

### 10.3 Hugging Face — passive inbound
**Goal:** Well-described dataset card, sample usage notebooks, link to TickerTruth for full access. Every download is a warm lead — add their email to your list if captured.

---

### 10.4 Reddit — community engagement (not direct selling)
**Subreddits:** r/algotrading, r/IndiaInvestments, r/quant  
**Goal:** 1 post/week max; add value in comments where relevant; share the free report, not a product pitch

---

### 10.5 Direct outreach — highest and fastest conversion channel
**Target list:** Build in Airtable (Section 2). Work it every Tuesday and Thursday.  
**Channels:** LinkedIn DM first, cold email if LinkedIn DM not delivered, Calendly for call  
**Goal weeks 1–4:** 20–30 messages/week; every reply gets a free sample within 2 hours

---

## 11. Content Calendar — Weeks 1–12

### Weeks 1–4 (Sprint Phase — first customer)

| Day | Platform | Content |
|---|---|---|
| Day 1–2 | Internal | Fix payment infra, delivery model, onboarding doc, pricing CTA |
| Day 3 | LinkedIn | **Post 1:** "Why India backtests break" |
| Day 3 | Outreach | Batch 1: 20 DMs to Tier 1 targets |
| Day 7 | LinkedIn | **Post 2:** "Corporate actions are not just dividends and splits" |
| Day 7 | Outreach | Batch 2: 25 DMs to Tier 2 targets |
| Day 7 | GitHub | Polish README with Loom demo embed |
| Day 10 | LinkedIn | **Post 3 (Loom video):** 5-minute demo — adjusted vs raw price after a bonus issue |
| Day 10 | Outreach | Second touch on Batch 1 non-replies (Template B with data hook) |
| Day 14 | LinkedIn | **Post 4:** "Survivorship bias — the graveyard problem" |
| Day 14 | Outreach | Batch 3: 25 DMs to Tier 2/3 targets |
| Day 14 | Hugging Face | Update dataset card with Loom demo link |
| Day 14 | Email | Lead magnet live on tickertruth.com |
| Day 15 | Outreach | Third touch on Batch 1 (Template E, final) |
| Day 18 | Communities | Post in QuantInsti community, r/algotrading, 1 Telegram group |
| Day 21 | LinkedIn | **Post 5:** "TickerTruth first public release — what's in it" (pricing, founding customer) |
| Day 21 | Outreach | Batch 4: 20 Tier 4 (indie quants) |
| Day 21 | CFA India | Submit talk proposal |
| Day 28 | Internal | Sprint review: calls, demos, trials, payment conversations. Convert. |

### Week 5 — Technical Depth

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 6:** "How to join symbol lineage to your price series in 5 lines of pandas" |
| Wed | GitHub | Publish `adjusted_vs_raw_series.ipynb` |
| Fri | LinkedIn | Chart snippet: "Adjusted vs raw price after a bonus issue" |

### Week 6 — Social Proof

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 7:** "What early users found in their NSE data" (anonymized) |
| Tue | Outreach | Batch 5: follow up on all warm leads from weeks 1–4 |
| Thu | Reddit | Reply in r/IndiaInvestments backtesting threads |
| Fri | LinkedIn | Pricing post with founding customer remaining slots count |

### Week 7 — Educational Series

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 8:** "Rights issues, face-value changes, NCLT restructurings — the corporate actions your vendor ignores" |
| Wed | LinkedIn | Poll: "What's the biggest pain with India historical data?" |
| Fri | LinkedIn | Poll results with commentary |

### Week 8 — Monthly Release Highlight

| Day | Platform | Content |
|---|---|---|
| Mon | LinkedIn | **Post 9:** Monthly release post with specific stats |
| Tue | Outreach | Batch 6: second-tier broker research teams |
| Thu | Hugging Face | Update with latest snapshot |

### Weeks 9–12 — Steady State

Continue 2 LinkedIn posts/week, 20 outreach DMs/week, 1 community post/week, 1 GitHub notebook/month. Monthly release post on release day.

---

## 12. Content — Full Drafts

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
> We built TickerTruth to fix this. Versioned reference-data layer for NSE equities: symbol lineage, corporate action events, and adjustment factors — released monthly with a full changelog.
>
> Free sample dataset at the link. Founding customer pricing: INR 10,000/month (5 slots, 2 taken).
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

### Post 3 — LinkedIn (Loom video)
**"5-minute demo: what adjusted vs raw price actually looks like after a bonus issue"**

---

> I made a short video showing exactly what breaks — and how TickerTruth fixes it.
>
> In 5 minutes: load a raw NSE price series → spot the discontinuity from a bonus issue → apply the adjustment factor → get a clean continuous series.
>
> Then the lineage join: map a renamed ticker to its entity ID so the backtest tracks the company, not the ticker string.
>
> This is the data problem most India quant teams have accepted as "good enough." It isn't.
>
> [5-min Loom demo link]
>
> Full dataset at tickertruth.com. Founding customer pricing (INR 10k/month) still available for 3 more slots.

**Hashtags:** #QuantFinance #NSE #AlgoTrading #DataEngineering #IndiaMarkets

---

### Post 4 — LinkedIn
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

### Post 5 — LinkedIn
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
> What's in the paid release (Starter, INR 15,000/month — or INR 10,000/month for founding customers):
> — Full historical lineage from 2000
> — Full corporate action event table (all action types, all years)
> — Backtest-ready adjustment factor map
> — Listing status history including delistings and mergers
> — Monthly release + changelog delivered to your inbox
>
> Founding customer pricing: INR 10,000/month locked for 12 months. 5 slots total. 2 taken.
>
> Full release notes: tickertruth.com/release-notes
> Pricing: tickertruth.com/pricing

**Hashtags:** #IndiaData #NSE #QuantFinance #DataProduct #OpenData

---

### Post 6 — LinkedIn
**"How to join symbol lineage to your price series in 5 lines of pandas"**

---

> The most common question: "How do I actually use the lineage table?"
>
> Here's the pattern:
>
> ```python
> import pandas as pd
>
> lineage = pd.read_parquet("dim_symbol_alias.parquet")
> prices  = pd.read_parquet("fact_equity_eod.parquet")
>
> prices_with_entity = prices.merge(
>     lineage[["symbol", "entity_id", "valid_from", "valid_to"]],
>     on="symbol", how="left"
> ).query("date >= valid_from and date < valid_to")
>
> continuous = prices_with_entity.groupby(["entity_id", "date"])["close"].last()
> ```
>
> Your backtest now tracks the entity, not the ticker string. Name changes, mergers, and renames don't break the series.
>
> Full sample notebook: [GitHub link]
> Full dataset: tickertruth.com

**Hashtags:** #Python #Pandas #QuantFinance #NSE #DataEngineering

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

### Post 8 — LinkedIn (Monthly Release — template, update each month)
**"Monthly release is out — here's what changed"**

---

> TickerTruth [Month] release is live at tickertruth.com/release-notes
>
> This month:
> — [X] securities in the master (updated from [Y] last month)
> — [N] corporate action events processed
> — [N] new adjustment factors computed
> — [N] symbol lineage events (renames, mergers, delistings)
>
> Notable this month:
> — [One specific interesting finding]
>
> Subscribers received the full release package by email.
>
> Founding customer pricing still available for [N] slots: INR 10,000/month. tickertruth.com/pricing

**Hashtags:** #IndiaData #NSE #DataRelease #QuantFinance #CorporateActions

---

### Post 9 — LinkedIn
**"NSE data sources compared — what each gives you and what each misses"**

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
> ✗ Often $20k–$100k/year  
> ✗ India edge cases are often wrong  
> ✗ No changelog — silent corrections with no audit trail  
>
> **Free open datasets (Yahoo Finance, other scrapers)**
> ✓ Free  
> ✗ No corporate action events, only price adjustments (no explanation)  
> ✗ No lineage — dead tickers just disappear  
> ✗ No versioning — last week's data may be silently different from today's  
>
> **TickerTruth**
> ✓ Full lineage and corporate action taxonomy (NSE + BSE)  
> ✓ Adjustment factors with event provenance  
> ✓ Versioned monthly with a full changelog  
> ✓ INR-priced, India-focused  
> ✗ Monthly cadence (not real-time)  
>
> We're not the right fit for real-time feeds. We are the right fit for the reference layer underneath your analytics.
>
> tickertruth.com

**Hashtags:** #IndiaData #NSE #DataVendor #QuantFinance #DataEngineering

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
> — 1 strategy has 18 months of live history contaminated by survivorship bias: backtest P&L was overstated by ~15%
>
> Conservative cost: 20 person-days of senior talent + an overfit strategy that underperformed its backtest.
>
> The reference data problem is not a data problem. It's an engineering and research reliability problem.
>
> TickerTruth Starter: INR 10,000/month (founding pricing). Less than one day of that analyst's time.
>
> tickertruth.com/pricing

**Hashtags:** #DataQuality #QuantFinance #CostOfBadData #IndiaEquities #NSE

---

### Post 11 — LinkedIn
**"Event-study methodology using correct corporate action dates"**

---

> A common pattern in quant research: measure abnormal returns around a corporate event.
>
> The silent killer: most teams use the *announcement date* when they should use the *ex-date* (or record date). For some event types, these differ by weeks.
>
> TickerTruth provides both dates for every event: announced_date, ex_date, record_date, payment_date — whichever are available from NSE filings.
>
> The difference in CAR[-5,+5] between announcement-date and ex-date alignment is often 3–4% on a typical bonus issue. That's not noise — it's a measurement error that corrupts your strategy.
>
> Sample notebook: [GitHub link]

**Hashtags:** #EventStudy #QuantFinance #NSE #CorporateActions #AlgoTrading

---

### Post 12 — LinkedIn (Week 12 review)
**"12 weeks of TickerTruth — what we've shipped and what's next"**

---

> Quick update on where TickerTruth is after the first quarter:
>
> — [N] monthly releases shipped
> — [N] paying subscribers
> — NSE + BSE coverage live
> — [Notable finding from real data]
>
> Next quarter: [BSE ISIN bridge / full CA history / API delivery — pick the one most requested by customers]
>
> If you've been following along and haven't tried it yet, now's the time. tickertruth.com/pricing

**Hashtags:** #IndiaData #QuantFinance #NSE #BSE #DataProduct

---

## 13. Outreach — Follow-up Sequence

For every prospect contacted, track through this sequence in Airtable:

| Touch | Day | Action | Template |
|---|---|---|---|
| 1 | Day 0 | Initial DM or email | Template A, C, or D |
| 2 | Day 4 | Follow-up with specific data hook | Template B |
| 3 | Day 10 | Final message, attach free report, soft close | Template E |
| — | Day 40 | Revive if they engage with LinkedIn content | New DM referencing the post |

**Rule:** Never send a fourth touch within the first 30 days. If they haven't replied after 3 touches, mark as "dormant" and move on. Re-engage if they like or comment on a LinkedIn post.

---

## 14. Weekly Rhythm — Ongoing (After Week 12)

| Cadence | Action |
|---|---|
| Every Monday | Publish 1 LinkedIn post |
| Every Tuesday + Thursday | 10 outreach DMs each day (20/week) |
| Monthly (on release day) | LinkedIn release post + HF dataset update + subscriber email |
| Monthly | 1 sample notebook or walkthrough on GitHub |
| Quarterly | Review: follower growth, inbound leads, conversion from outreach |
| Quarterly | Conference/meetup talk (CFA India, QuantInsti webinar) |

---

## 15. Success Metrics

### 4-Week Sprint Targets (first priority)

| Metric | Target |
|---|---|
| Outreach messages sent | 90+ |
| Demo calls booked | 5+ |
| Free samples sent | 15+ |
| Paying customers | 1 |

### 90-Day Targets

| Metric | Target |
|---|---|
| LinkedIn followers (net new, targeted) | 300–500 |
| LinkedIn post impressions (avg per post) | 1,000+ |
| Hugging Face dataset downloads | 200+ |
| Lead magnet downloads (email captures) | 50+ |
| Direct outreach conversations started | 150+ |
| Paying customers | 3–5 |
| Website unique visitors/month by week 12 | 500+ |

---

## 16. Tools

| Tool | Purpose | Cost |
|---|---|---|
| Razorpay | INR payment collection + UPI | Free to set up, 2% per transaction |
| Stripe | International card payments | Free to set up, 2.9% + $0.30 |
| Calendly | Demo call booking, embedded in outreach | Free tier |
| Loom | 5-minute demo recording | Free |
| ConvertKit (free tier) | Email list for lead magnet | Free up to 1,000 subscribers |
| Airtable | Outreach CRM — track all 150 contacts | Free tier |
| LinkedIn personal profile | All B2B content and DMs | Free |
| GitHub (existing) | Credibility, notebooks, README | Free |
| Hugging Face (existing) | Passive discovery | Free |
| Canva | Charts for LinkedIn posts | Free tier |

---

## 17. Red Lines (What Not to Do)

- Do not start outreach before payment infra is live — getting a yes and then stumbling kills deals
- Do not offer 3-month free design-partner access — offer a 7-day sample + 30-day money-back instead
- Do not cold-spam LinkedIn connections without a personalized hook
- Do not pitch in Reddit comments — add value first, link only when directly relevant
- Do not claim real-time data coverage — TickerTruth is a monthly reference product
- Do not compare directly to Bloomberg/Refinitiv on price or scale — compete on India-specificity and transparency

---

## 18. Implementation Plan and Todos

Organized by phase. Complete each phase in order — later phases depend on earlier ones being done. Estimated times are realistic single-person effort.

---

### Phase 0 — Revenue Unblocking (Day 1–2, ~6 hours total)
**Must be done before any outreach. Do not skip or defer.**

#### Payment collection
- [ ] Create Razorpay account at razorpay.com. Required: PAN card, bank account details, business email. KYC approval takes 1–2 business days — start today.
- [ ] Once Razorpay is approved: create a "Founding Starter" recurring payment link at INR 10,000/month.
- [ ] Create a "Standard Starter" recurring payment link at INR 15,000/month.
- [ ] Create a Stripe account at stripe.com for international customers (card + USD billing). No KYC delay.
- [ ] Create Stripe recurring payment links mirroring the Razorpay tiers (use USD equivalent, e.g. $120/month founding, $180/month standard).
- [ ] Test both payment flows end-to-end with a test card before using in outreach.

#### Subscriber delivery
- [ ] Decide: R2 presigned links delivered by email is the MVP delivery method. No portal needed for the first 10 customers.
- [ ] Write a short Python script (or Cloudflare Worker function) that accepts an email address + release date → generates a time-limited R2 presigned URL → sends an email with the URL. Does not need to be automated; a manual script you run once per new subscriber is fine for now.
- [ ] Test the script with a dummy zip from R2 to confirm the link works and expires correctly.
- [ ] Document the manual process: "New subscriber arrives → run script → send onboarding email." One Notion page or Google Doc is enough.

#### Onboarding document
- [ ] Write `docs/subscriber-onboarding.md` — target 1 page. Contents:
  - What files are in the release package (list each file and its schema)
  - How to load each file (one pandas code snippet per file)
  - How to do the lineage join (the 5-line snippet from Post 6)
  - Release schedule (first business day of each month)
  - Support contact email
  - 30-day money-back policy statement
- [ ] Export as PDF (Pandoc or manual) — this is what you email to new subscribers on day 1.

#### Pricing page CTA
- [ ] Set up Calendly free account. Create a 20-minute event: "TickerTruth Demo Call." Add description: "I'll walk through the product with a live data example relevant to your use case."
- [ ] Add Calendly link to: LinkedIn bio, LinkedIn featured section, tickertruth.com/pricing, outreach DM templates.
- [ ] Update tickertruth.com/pricing: add a "Buy now" button to the Starter card that links to the Razorpay founding payment link.
- [ ] Add a founding slot counter to the Starter card: "X of 5 founding slots available at INR 10,000/month." Update manually as slots fill.
- [ ] Add a "Book a 20-min call first" secondary link below the buy button for prospects who aren't ready to pay without a demo.

---

### Phase 1 — Outreach Infrastructure (Day 2–3, ~4 hours total)

#### Airtable CRM
- [ ] Create a free Airtable base named "TickerTruth Outreach CRM." Add these fields:
  - Name (text)
  - Company (text)
  - Role (text)
  - Tier (select: 1 / 2 / 3 / 4)
  - LinkedIn URL (URL)
  - Email (text, fill in when known)
  - Touch 1 Date (date) + Template Used (select: A/B/C/D/E)
  - Touch 2 Date + Hook Note (text — what specific hook you used)
  - Touch 3 Date
  - Status (select: Prospect / Contacted / Replied / Demo Booked / Trial Sent / Negotiating / Paid / Dead / Dormant)
  - Notes (long text)
- [ ] Create a view: "Sprint Week 1 — Batch 1" filtered to Tier 1, sorted by Status.
- [ ] Create a view: "Follow-up Due" filtered to Touch 1 Date ≤ today-4 AND Status = Contacted.
- [ ] Create a view: "Active Leads" filtered to Status in {Replied, Demo Booked, Trial Sent, Negotiating}.

#### Building the contact list
Work through the Section 2 target companies and add real names. Budget ~15 minutes per company.

- [ ] **Tier 1 (8 companies) — 2 hours.** For each: LinkedIn search "[Company Name] quant" or "[Company Name] data" or "[Company Name] research." Find the Head of Quant / Head of Research / Head of Data. Add name + LinkedIn URL to Airtable.
  - DSP Quant Fund
  - Nippon India Quant
  - Edelweiss AIF
  - Marcellus Investment Managers
  - Quantum AMC
  - Axis AMC systematic
  - Motilal Oswal AMC quant
  - White Oak Capital
- [ ] **Tier 2 (7 companies) — 90 minutes.** Same process.
  - Smallcase Technologies
  - Streak / AlgoLab
  - Sensibull
  - Dhan
  - Fyers
  - AlgoTest
  - INDmoney
- [ ] **Tier 3 (5 companies) — 60 minutes.**
  - Kotak Securities Research
  - ICICI Securities Research
  - Emkay Global
  - Spark Capital
  - JM Financial
- [ ] **Tier 4 (20 indie quants) — 45 minutes.** LinkedIn search: "algorithmic trading India NSE" filter by posts in last 30 days. Also: QuantInsti EPAT alumni who post about Python or backtesting. Target people actively building, not just consuming.

#### LinkedIn profile
- [ ] Update headline: "Building TickerTruth — versioned NSE + BSE reference data for quant teams and fintech data engineers"
- [ ] Update About section: lead with the pain ("Most India quant teams are backtesting on data that silently breaks at mergers, renames, and delistings — we built TickerTruth to fix that."), then product description, then call to action with Calendly link.
- [ ] Add tickertruth.com to the Website field in Contact Info.
- [ ] Add Calendly link to Featured section.
- [ ] Connect with all Tier 1 and Tier 2 prospects (connection request, no message yet) at least 48 hours before sending the first DM. Connection + DM in the same moment looks automated.

---

### Phase 2 — Content Assets (Day 3–5, ~8 hours total)

#### Loom demo (highest-priority content asset — do this before any LinkedIn posts)
- [ ] Write a 5-minute script. Sections:
  1. (0:00–0:30) Setup: "I'm going to show you what a raw NSE price series looks like when a company has a bonus issue — and what happens to your backtest."
  2. (0:30–1:30) Load the raw price series for a real NSE stock with a known bonus issue. Show the discontinuous drop. "Your backtest reads this as a 50% loss. It didn't happen."
  3. (1:30–3:00) Load the TickerTruth adjustment factor table. Apply the factor. Show the corrected series on the same chart. "This is what actually happened to price."
  4. (3:00–4:00) Load `dim_symbol_alias.parquet`. Do the lineage join. Show the same company tracked across a rename — entity_id stays constant, ticker changes. "Your strategy now follows the company, not the ticker string."
  5. (4:00–4:30) Show the corporate action event table row: action_type, ex_date, factor, confidence_flag. "Every factor has a provenance — you know what event caused it, on what date, at what confidence."
  6. (4:30–5:00) "This is tickertruth.com. Free sample on the site. Founding customer pricing available now."
- [ ] Use `notebooks/broken_vs_corrected_backtest.ipynb` as the live demo. Run through it once before recording to confirm it works cleanly.
- [ ] Record in one take on Loom. Rough is fine — do not spend more than 2 hours recording/retaking.
- [ ] Upload to Loom. Set visibility: public, anyone with link. Copy the share URL.
- [ ] Embed on tickertruth.com homepage, above the fold, before the features section.
- [ ] Add Loom URL to GitHub README (as a video thumbnail if possible, otherwise a plain link).

#### Lead magnet — "India Backtest Integrity Report"
- [ ] Outline the PDF (6–8 pages):
  - Cover: "India Backtest Integrity Report: 5 common NSE data errors and how to detect them in your own pipeline"
  - Error 1: Symbol discontinuity at merger/rename. Real example: HDFC Ltd → HDFC Bank merger. What breaks, what to check.
  - Error 2: Bonus issue mislabeled as stock split. Formula comparison: bonus adjustment ≠ split adjustment. How to detect it.
  - Error 3: Survivorship bias from dropped delistings. Quantified: how much does Sharpe inflate when dead tickers are excluded? Use a back-of-envelope calculation.
  - Error 4: Announcement date vs ex-date misalignment. CAR window shifts by 1–3 weeks for many event types. How to detect it.
  - Error 5: Face-value change not tracked as a price adjustment. Often treated as no-op; actually breaks the adjusted series.
  - Audit checklist: "Run these 5 checks on your price series today" — one code snippet per check, all in pandas.
  - Last page: "TickerTruth handles all five. Free sample at tickertruth.com/pricing."
- [ ] Write the content (target: 800–1200 words total across all pages — this is a checklist, not a whitepaper).
- [ ] Design in Canva. Use website brand colors. Keep it clean — no clip art, no stock photos.
- [ ] Export as PDF.
- [ ] Set up ConvertKit free account at convertkit.com.
- [ ] Create a ConvertKit form: title "Get the free India Backtest Integrity Report," one field (email address).
- [ ] Create a ConvertKit automation: on form submit → send email with PDF download link (host the PDF on R2 or GitHub). Tag subscriber as "lead-magnet."
- [ ] Create a landing page at tickertruth.com/integrity-report. A single Cloudflare Pages page with: 5-bullet summary of what's in the report, ConvertKit form embed, Loom video embed above the fold.
- [ ] Add the integrity report link to: LinkedIn bio, every LinkedIn post footer (one line: "Free audit report: tickertruth.com/integrity-report"), GitHub README, Hugging Face dataset card.

---

### Phase 3 — Sprint Week 1 (Days 3–7, ~3 hours/day)

#### LinkedIn content
- [ ] **Day 3 — publish Post 1** ("Why your India backtest is lying to you," Section 12). Add founding customer pricing and Calendly link to post footer. Publish at 9:00 AM IST (peak India LinkedIn time).
- [ ] After posting: stay on LinkedIn for 60 minutes. Reply to every early comment within the hour — the LinkedIn algorithm heavily weights early engagement velocity.
- [ ] **Day 7 — publish Post 2** ("Corporate actions are not just dividends and splits," Section 12). Same timing.

#### Outreach Batch 1 (Day 3, 20 DMs)
- [ ] Send 20 personalized DMs using Template A (Section 7). For each DM:
  - Personalize the opening with one specific detail from their profile: a recent post they made, a project they mentioned, a company they moved from. Generic DMs get ignored.
  - Copy their name and company into Airtable. Set status to "Contacted." Set Touch 1 Date.
- [ ] **Do not send 20 DMs in a single LinkedIn session.** LinkedIn flags rapid-fire DMing as spam. Send in batches of 5–7 across 3 sessions over the day.

#### Outreach Batch 2 (Day 7, 25 DMs)
- [ ] Send 25 DMs to Tier 2 targets (Template A for data engineers, Template C for indie quants).
- [ ] Log all in Airtable.

#### Touch 2 follow-up on Batch 1 (Day 7)
- [ ] Open Airtable "Follow-up Due" view. For every Batch 1 contact with no reply:
  - Send Template B. Personalize the data hook. Example: if they work at a pharma-focused fund, say "We found 4 pharma tickers in the Nifty 500 that changed names or merged in 2023 — thought this might be relevant."
  - Set Touch 2 Date in Airtable.

---

### Phase 4 — Sprint Week 2 (Days 8–14, ~3 hours/day)

#### Content
- [ ] **Day 10 — publish Post 3** (Loom video post, Section 12). Lead with the video. Include founding customer slot count. Publish at 9:00 AM IST.
- [ ] **Day 14 — publish Post 4** ("Survivorship bias — the graveyard problem," Section 12).

#### Outreach
- [ ] **Day 11 — Touch 2 on Batch 2 non-replies** (Template B, personalized data hook per contact).
- [ ] **Day 10 — Touch 3 on Batch 1 non-replies** (Template E): final message. Attach lead magnet. Soft close on founding-customer window. Mark non-repliers as "Dormant" in Airtable.
- [ ] **Day 14 — Batch 3** (25 DMs to Tier 2/3 contacts + any warm referrals from Week 1 replies).

#### Hugging Face update (Day 14)
- [ ] Update dataset card: add Loom demo URL, add lead magnet URL, update sample statistics if a new release has run.
- [ ] Note current download count as a baseline for Week 4 review.

#### Community seeding (Day 14)
- [ ] **r/algotrading:** Post the "broken backtest" problem as a genuine finding with data. Title: "I dug into NSE corporate action data quality — here's what I found." Share the Loom demo in the post, not the product pricing. Let people ask about the tool in comments.
- [ ] **QuantInsti community forum:** Post the free Integrity Report link with a short intro. Do not pitch the product; let the report do the work.
- [ ] **QuantInsti content team:** Send an email to their content or community team proposing a free 45-minute webinar for EPAT alumni: "India reference data quality — the hidden problems in your backtest pipeline." Find contact at quantinsti.com/contact or LinkedIn search "QuantInsti content."

---

### Phase 5 — Sprint Week 3 (Days 15–21, ~3 hours/day)

#### Content
- [ ] **Day 18 — no new LinkedIn post.** Use the slot to engage in comments on posts 1–4 and reply to any DMs or inbound from community seeding.
- [ ] **Day 21 — publish Post 5** ("TickerTruth first public release," Section 12). Include exact founding slot count remaining. This is the product announcement post — get the timing right.

#### Outreach
- [ ] **Day 15 — Touch 2 on Batch 3 non-replies** (Template B).
- [ ] **Day 21 — Batch 4** (20 DMs to Tier 4 indie quants using Template C). These are fast decisions — aim to book demo calls within the same week.

#### CFA India and CMT (Day 21)
- [ ] Find CFA Society India events coordinator: search LinkedIn "CFA Society India events" or check cfasociety.org/india. Send a talk proposal email: "India equity reference data quality — a case study for quant analysts" (proposed duration: 25–30 minutes + Q&A).
- [ ] CMT Association India: submit the same proposal to their events contact. Search LinkedIn "CMT Association India."
- [ ] Note: these events will be 6–8 weeks out if accepted. Start now so the talk lands in weeks 7–10.

#### Demo calls (this week and next)
- [ ] For every Calendly call booked:
  - Send the free 7-day sample *before* the call (24 hours ahead) so they've seen the data.
  - Prepare one personalized data point: look up a corporate action or lineage event relevant to the company or sector they focus on.
  - During the call: ask "What does your current data pipeline look like for corporate actions?" before demoing. Let them describe their pain first.
  - End with: "Want to start the founding customer subscription this week? I have [N] slots left at INR 10,000/month."
- [ ] After each call: send a follow-up email within 2 hours. Include payment link, onboarding doc, and a single sentence summarizing what you discussed.

---

### Phase 6 — Sprint Week 4 — Convert (Days 22–28)

- [ ] **Touch 3 on Batch 2 non-replies** (Template E, final touch, attach lead magnet).
- [ ] **Touch 2 on Batch 4 Tier 4 non-replies** (Template B).
- [ ] **Follow up on all trial samples sent in weeks 1–3.** Message: "How is the sample working for you? Happy to jump on a quick call or answer questions by message."
- [ ] For every warm lead (status: Replied, Demo Booked, Trial Sent): add a specific next action in Airtable notes and work through each one this week.
- [ ] **Day 28 — Sprint review.** Fill out this table:

  | Metric | Target | Actual |
  |---|---|---|
  | Outreach messages sent | 90+ | |
  | Replies received | 15+ | |
  | Demo calls booked | 5+ | |
  | Free samples sent | 15+ | |
  | Paying customers | 1 | |

- [ ] Update founding customer slot count on tickertruth.com/pricing.
- [ ] For any warm leads not yet closed: move to "Week 5 priority" list in Airtable with a specific next action and date.

---

### Phase 7 — Ongoing Infrastructure (parallel to sprint, not blocking)

These can be done in spare time during weeks 1–4. None of them block the sprint.

#### GitHub
- [ ] Add the Loom demo video thumbnail (or GIF preview) to the README header.
- [ ] Add a "Free sample" badge: `[![Free Sample](https://img.shields.io/badge/Free_Sample-tickertruth.com-blue)](https://tickertruth.com)`.
- [ ] Add "Download the India Backtest Integrity Report" as a line in the README, linking to tickertruth.com/integrity-report.
- [ ] Confirm all four notebooks have working Colab badges (from the todo.md — already done in commit `f2f3325`, but verify links are live).
- [ ] Pin the repository on the GitHub profile page.

#### Analytics setup
- [ ] Enable Cloudflare Web Analytics on tickertruth.com (free, already on Cloudflare Pages — toggle it on in the Pages settings). No code changes needed.
- [ ] Set up a weekly 30-minute "metrics review" block every Friday. Check:
  - Cloudflare: unique visitors, top pages, referral sources
  - LinkedIn Analytics: impressions per post, follower count, DM reply rate
  - Hugging Face: dataset downloads
  - ConvertKit: new subscribers, open rate
  - Airtable: outreach count, reply rate, demo conversion rate, paying customers

#### BSE LinkedIn posts (from todo.md B8 — schedule for weeks 7–8)
- [ ] Draft "BSE-only listings your backtest is missing" LinkedIn post (referenced in todo.md B8).
- [ ] Draft "When NSE and BSE disagree on the record date" LinkedIn post (referenced in todo.md B8).
- [ ] Schedule both for the Week 7–8 content slots in Section 11.

#### Substack (optional — start only if LinkedIn is driving engagement by week 3)
- [ ] Create Substack at tickertruth.substack.com. Publish Post 1 as the first issue (copy from LinkedIn, add 2–3 extra paragraphs of depth).
- [ ] Add Substack link to LinkedIn and GitHub.
- [ ] Import ConvertKit lead-magnet subscribers into Substack (or consolidate to one platform — pick one and stick with it).

---

### Implementation Checklist Summary

Use this as a quick-scan status board.

**Day 1–2 (Phase 0 — must complete before outreach):**
- [ ] Razorpay account created and KYC submitted
- [ ] Stripe account created and payment links live
- [ ] R2 delivery script written and tested
- [ ] Subscriber onboarding doc written (`docs/subscriber-onboarding.md`)
- [ ] Calendly event created (20-min demo call)
- [ ] tickertruth.com/pricing updated with Buy Now button + slot counter + Calendly link

**Day 2–3 (Phase 1 — outreach infrastructure):**
- [ ] Airtable CRM created with all fields and views
- [ ] Tier 1 contact list populated (8 companies, real names + LinkedIn URLs)
- [ ] Tier 2 contact list populated (7 companies)
- [ ] Tier 3 contact list populated (5 companies)
- [ ] Tier 4 indie quant list populated (20 contacts)
- [ ] LinkedIn profile updated (headline, About, Calendly in Featured)
- [ ] All prospects connected on LinkedIn (48h before first DM)

**Day 3–5 (Phase 2 — content assets):**
- [ ] Loom demo script written
- [ ] Loom demo recorded and uploaded
- [ ] Loom embedded on tickertruth.com homepage
- [ ] India Backtest Integrity Report PDF written and designed
- [ ] ConvertKit account set up and automation live
- [ ] Lead magnet landing page at tickertruth.com/integrity-report live
- [ ] Lead magnet link added to LinkedIn bio, GitHub README, HF dataset card

**Day 3 (Sprint start):**
- [ ] LinkedIn Post 1 published (9:00 AM IST)
- [ ] Outreach Batch 1 sent (20 DMs, Tier 1 targets, Template A)

**Day 7:**
- [ ] LinkedIn Post 2 published
- [ ] Outreach Batch 2 sent (25 DMs, Tier 2 targets)
- [ ] Touch 2 sent on Batch 1 non-replies (Template B, personalized hook)

**Day 10:**
- [ ] LinkedIn Post 3 published (Loom video)
- [ ] Touch 3 sent on Batch 1 non-replies (Template E, final)

**Day 14:**
- [ ] LinkedIn Post 4 published
- [ ] Outreach Batch 3 sent (25 DMs)
- [ ] Hugging Face dataset card updated
- [ ] r/algotrading post published
- [ ] QuantInsti community post + webinar pitch email sent

**Day 21:**
- [ ] LinkedIn Post 5 published (product launch, founding customer slots)
- [ ] Outreach Batch 4 sent (20 Tier 4 DMs)
- [ ] CFA India and CMT talk proposal emails sent

**Day 28 (Sprint close):**
- [ ] Sprint review completed (metrics table filled in)
- [ ] All warm leads have a next action in Airtable
- [ ] Founding customer slot count updated on website
- [ ] Week 5 priority list defined
- Do not keep outreach at 10/week — at that rate, first customer takes 3–4 months, not 4 weeks
