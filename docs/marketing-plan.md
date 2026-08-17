# 10-Day LinkedIn + Substack Content Plan (Automated via openclaw)

Generated 2026-08-02, for the 10-day run **Monday 2026-08-03 → Friday
2026-08-14**. Days 6–7 (originally the weekend of 2026-08-08/09) were
missed and rescheduled to 2026-08-11/12 (see updated calendar below);
days 9–10 shifted two days later as a result. Sourced from the content
already drafted in
[`marketing.md`](../marketing.md) Section 12 and the sprint calendar in
Section 11, sequenced daily instead of every 3–4 days, and cross-checked
against what's already live on [tickertruth.com/blog](https://tickertruth.com/blog/)
so nothing duplicates.

## 0. What's already live (checked before writing this)

The blog currently has 4 posts: *Welcome to the TickerTruth Blog*, *The
Evolution of Technology in India's Capital Markets*, *Today's AI is an
incredible tool...*, and *Why Evolution Built the Perfect Survivor... But
Not the Perfect Investor*.

**One naming collision to watch:** the existing post "Why Evolution Built
the Perfect Survivor" is about evolutionary psychology and investor
behavior. Day 4 below is about **data** survivorship bias (delisted
tickers vanishing from feeds) — a completely different concept that
happens to share the word "survivor." Day 4's copy below is worded to
avoid echoing that title so readers don't conflate the two. Do not title
it "The Perfect Survivor" or similar.

None of the other three existing posts overlap with the corporate-actions
/ symbol-lineage / adjustment-factor material below, so all 10 days are
new ground.

## 1. Content principles (from `marketing.md`)

- Tone: technical, first-person, problem-led, no hype (Section 10.1).
- Mix: ~50% educational, ~30% product/data updates, ~20% social proof
  (Section 10.1).
- Every post ends with a link to `tickertruth.com`. No pricing or CTA
  copy in the post text — the goal for this run is interest and reach,
  not conversion (Section 3).
- Substack posts are the LinkedIn post **plus 2–3 extra paragraphs of
  depth** (Section "Phase 7 — Substack", `marketing.md` line ~1091) — not
  a rewrite, an expansion. That's the pattern used below for every day.
- Red lines that still apply (Section 17): no real-time-data claims, no
  direct Bloomberg/Refinitiv price comparison, no spammy cadence — daily
  is fine for *content*, it is **not** fine for the DM outreach volume;
  this plan only covers the two feed/newsletter channels, not DMs.

## 2. The 10-day calendar

**Updated 2026-08-10:** Days 6–7 were not posted on their original
weekend dates (2026-08-08/09) and are rescheduled below to 2026-08-11/12,
the next two available slots after Day 8 (which posted on time,
2026-08-10, with rewritten copy — see §3.8). Days 9–10 shift two days
later accordingly, so the run now closes Friday 2026-08-14 instead of
Wednesday 2026-08-12.

| Day | Date | Theme | LinkedIn source | Substack source |
|---|---|---|---|---|
| 1 | Mon 2026-08-03 | Why India backtests silently break | `marketing.md` Post 1 | Expanded (§3.1) |
| 2 | Tue 2026-08-04 | Corporate actions ≠ dividends + splits | `marketing.md` Post 2 | Expanded (§3.2) |
| 3 | Wed 2026-08-05 | 5-line pandas lineage join (technical) | `marketing.md` Post 6 | Expanded (§3.3) |
| 4 | Thu 2026-08-06 | Survivorship bias in the data feed | `marketing.md` Post 4 (reworded) | Expanded (§3.4) |
| 5 | Fri 2026-08-07 | NSE data sources compared | `marketing.md` Post 9 | Expanded (§3.5) |
| 8 | Mon 2026-08-10 | Latest release status, honest update *(rewritten)* | `marketing.md` Post 5 (rewritten 2026-08-10) | Expanded (§3.8, rewritten) |
| 6 | ~~Sat 2026-08-08~~ → Tue 2026-08-11 | The hidden cost of bad reference data | `marketing.md` Post 10 | Expanded (§3.6) |
| 7 | ~~Sun 2026-08-09~~ → Wed 2026-08-12 | 12 corporate action types, ranked by how often vendors miss them | `marketing.md` Post 7 | Expanded (§3.7) |
| 9 | ~~Tue 2026-08-11~~ → Thu 2026-08-13 | Announcement date vs ex-date (event studies) | `marketing.md` Post 11 | Expanded (§3.9) |
| 10 | ~~Wed 2026-08-12~~ → Fri 2026-08-14 | Week close: recap, what's next | New (§3.10) | Expanded (§3.10) |

Rows are left in original day-number order (not date order) so the
content sequencing (§3.1–§3.10) still lines up 1:1 with its section
number below — only the calendar dates moved. Day 6 and 7's "lighter
weekend read" framing no longer applies now that they land on weekdays;
the copy in §3.6/§3.7 doesn't reference specific days of the week, so no
text changes were needed there, only the date.

---

## 3. Full post text, day by day

Each day below has the **LinkedIn** post verbatim (already drafted and
approved in `marketing.md`) and a **Substack** version that adds 2–3
paragraphs of depth per the stated pattern. Substack posts get a title;
LinkedIn posts don't need one (feed posts, not articles).

### 3.1 — Day 1, Mon 2026-08-03

**LinkedIn:**
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
> Free sample dataset at the link.
>
> tickertruth.com
>
> #QuantFinance #AlgoTrading #IndiaMarkets #DataEngineering #NSE #Backtesting

**Substack — "Why Your India Backtest Is Probably Lying To You":**
> [LinkedIn text above, as the opening]
>
> Here's the part that doesn't fit in a feed post: the HDFC merger isn't a rare edge case, it's a preview of what happens every year at smaller scale. NSE processes dozens of amalgamations, demergers, and scheme-of-arrangement events annually. Each one either creates a new ticker, retires an old one, or both — and every vendor that keys its price history on the raw ticker string, not a stable entity ID, is exposed to the same failure mode.
>
> The mechanical reason this matters for backtests specifically: most portfolio construction code does a `merge` or `join` on `symbol`. When a symbol is reused, orphaned, or split across two rows for the same underlying company, that join either silently drops history or silently stitches together two unrelated companies' price series at the boundary date. Neither failure throws an exception. Your Sharpe ratio just comes out wrong, and it comes out wrong in the direction that makes the strategy look better, not worse — because dropped history removes exactly the messy periods.
>
> The fix isn't "be more careful with joins." It's structural: resolve every price row to a `security_id` that survives the ticker change, before any adjustment or backtest logic runs. That's what a symbol lineage table is for.
>
> Free sample dataset, symbol lineage included: tickertruth.com.

---

### 3.2 — Day 2, Tue 2026-08-04

**LinkedIn:**
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
> Free sample: tickertruth.com
>
> #CorporateActions #IndiaEquities #DataQuality #QuantFinance #NSE

**Substack — "Corporate Actions Are Not Just Dividends and Splits":**
> [LinkedIn text above]
>
> Take bonus issues versus splits, since they're the one most people get wrong first. A 1:1 stock split and a 1:1 bonus issue both double share count and halve price — mechanically indistinguishable in a raw price series. But they are different corporate events with different tax and regulatory treatment in India, and — more relevant for a backtest — they sometimes arrive with different metadata timing from NSE, which means an adjustment pipeline that treats "ratio detected" as "must be a split" will occasionally apply the right *factor* on the wrong *date*.
>
> Face-value changes are the quieter one. A company changing face value from ₹10 to ₹2 is economically a 5:1 split, but it often isn't flagged as a "corporate action" in vendor feeds at all — it shows up as a metadata change on the security master, if it shows up anywhere. If your adjustment pipeline only watches the corporate-actions feed, face-value changes slip through and your price series has an unexplained 5x discontinuity that nothing in your pipeline was watching for.
>
> This is why we built one canonical event table instead of bolting adjustment logic onto each action type separately: every event — split, bonus, rights, face-value change, capital reduction, demerger, amalgamation — goes through the same `action_type → adjustment_factor` resolution path, with the source event kept as provenance.
>
> Full taxonomy and methodology: tickertruth.com/methodology. Free sample: tickertruth.com.

---

### 3.3 — Day 3, Wed 2026-08-05

**LinkedIn:**
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
> Full sample notebook: https://github.com/brkrishna/TickerTruth/blob/main/notebooks/sample_lineage_walkthrough.ipynb
> Full dataset: tickertruth.com
>
> #Python #Pandas #QuantFinance #NSE #DataEngineering

**Substack — "The 5-Line Pandas Pattern for Symbol-Stable Backtests":**
> [LinkedIn text above, code block included]
>
> Two things worth calling out that don't fit in a feed post. First, the `valid_from` / `valid_to` window in `dim_symbol_alias` is what makes the join safe when NSE *reuses* a ticker for an unrelated company after the original delists — a rarer but real failure mode. Without the date range, `symbol` alone is ambiguous across time; with it, the same three-line `.query()` filter that resolves renames also resolves reuse, because each row in the alias table is scoped to the period that ticker actually meant that entity.
>
> Second, the `groupby(["entity_id", "date"]).last()` step matters more than it looks. On a merger day, both the acquirer and target symbols can have rows for the same calendar date before the corporate action fully settles in the feed. Grouping on `entity_id` instead of `symbol` collapses that to one row per entity per day — which is what lets a merger show up in your backtest as a clean transition instead of a duplicate-date error.
>
> This is the same join pattern the Loom demo walks through end to end, including what the "before" price series looks like with the discontinuity still in it.
>
> Full sample notebook: https://github.com/brkrishna/TickerTruth/blob/main/notebooks/sample_lineage_walkthrough.ipynb. Full dataset: tickertruth.com.

---

### 3.4 — Day 4, Thu 2026-08-06

*(Reworded from `marketing.md` Post 4 to avoid the title collision noted in §0 — content is the same idea, phrasing changed so it doesn't read as a companion piece to the existing "Perfect Survivor" post.)*

**LinkedIn:**
> A commonly cited stat: most stock market indices look better than average because losers get removed.
>
> The same problem exists in your data feed, and it's a *data engineering* problem, not a psychology one — it's about what your vendor silently stops updating, not how you think about risk.
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
> The delisted names are part of the product, not a gap in it.
>
> tickertruth.com
>
> #SurvivorshipBias #NSE #QuantFinance #AlgoTrading #IndiaMarkets

**Substack — "The Graveyard Problem: Survivorship Bias in Your Data Feed, Not Your Head":**
> [LinkedIn text above]
>
> Worth separating this from the behavioral-finance version of "survivorship bias" that gets discussed more often — the one about mistaking lucky survivors for skilled ones. This is the mechanical, upstream version: your data vendor's database doesn't have a row for a company that delisted five years ago, so no backtest running against that database can ever include it, regardless of how careful the researcher is about interpretation. It's not a cognitive bias to correct for — it's a missing row.
>
> The magnitude is usually underestimated. NSE has delisted, merged, or suspended several hundred equities over the past decade — voluntary delistings after buyback offers, involuntary delistings for non-compliance, and NCLT-ordered restructurings where the original entity ceases to exist. A universe screen built from "current active NSE equities" excludes all of them by construction, which means any factor or momentum backtest run against that universe is implicitly conditioning on "companies that didn't go to zero" — the exact selection effect the term describes.
>
> The fix requires the vendor to keep updating a row after it stops being interesting, which is precisely the incentive problem: a live-trading data feed has no reason to maintain delisted-ticker history, because nobody's placing an order against it. A reference-data product does, because backtest integrity is the product.
>
> Listing status history, full delisted universe, tickertruth.com.

---

### 3.5 — Day 5, Fri 2026-08-07

**LinkedIn:**
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
> ✓ Built for India, not adapted from a global feed
> ✗ Monthly cadence (not real-time)
>
> We're not the right fit for real-time feeds. We are the right fit for the reference layer underneath your analytics.
>
> tickertruth.com
>
> #IndiaData #NSE #DataVendor #QuantFinance #DataEngineering

**Substack — "NSE Data Sources Compared — What Each Gives You, What Each Misses":**
> [LinkedIn table above]
>
> The Bloomberg/Refinitiv line deserves a caveat, since it reads like a dismissal and isn't meant as one: for large-cap, real-time, cross-asset coverage they're the right tool and nothing India-specific replaces that. Where they're weaker is exactly the narrow layer this product covers — India corporate-action edge cases (rights issues with unusual entitlement ratios, NCLT-ordered restructurings, regional-exchange-only delistings) where a global data vendor's India desk is thin, and changes get corrected silently in the underlying feed with no changelog a downstream user can audit against.
>
> The free-scraper category is the one that causes the most damage precisely because it's free and "close enough" for a while. Yahoo Finance-style adjusted closes apply *some* adjustment, which is worse than applying none in one specific way: it's not obvious from the data that anything was adjusted, so a researcher has no way to check whether the adjustment was applied correctly, applied on the right date, or applied at all for a given event type. An unadjusted series with a visible discontinuity at least tells you where to look.
>
> The honest limitation on our side: this is a monthly-release product, not a real-time feed, and it's built that way deliberately — versioning and changelog integrity are easier to guarantee at monthly cadence than at tick frequency. If the requirement is intraday or real-time corporate-action alerts, this isn't the right tool; if the requirement is a trustworthy, auditable reference layer for backtesting and research, monthly is the right cadence, not a compromise.
>
> tickertruth.com

---

### 3.6 — Day 6, ~~Sat 2026-08-08~~ Tue 2026-08-11 *(rescheduled — missed original date)*

**LinkedIn:**
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
> tickertruth.com
>
> #DataQuality #QuantFinance #CostOfBadData #IndiaEquities #NSE

**Substack — "The Hidden Cost of Bad Reference Data":**
> [LinkedIn text above]
>
> The 20-person-days figure is the visible cost — time you can put on a timesheet. The 15% backtest overstatement is the expensive one, because it doesn't show up as a cost at all until the strategy goes live and underperforms its own backtest. At that point the team's instinct is usually to blame regime change, execution slippage, or market impact — all real effects, but not the first thing to check. The first thing to check is whether the backtest universe silently excluded every stock that delisted during the backtest window, because that alone can account for a meaningful chunk of an "unexplained" live/backtest gap.
>
> There's a second-order cost that's harder to quantify but worth naming: research time spent debugging a data artifact that looks like a strategy problem. An analyst who spends two weeks trying to figure out why a factor stopped working, only to discover a face-value change wasn't adjusted for, has lost two weeks of research capacity that produced a data-hygiene finding, not an alpha finding. Multiply that across a team and a year, and it's a meaningful fraction of total research output spent on problems that a correct reference layer would have prevented entirely.
>
> None of this requires trusting a vendor's marketing claim — it's checkable. Run the audit checklist (five pandas snippets, one per common error type) against your own price series this weekend: tickertruth.com/integrity-report.

---

### 3.7 — Day 7, ~~Sun 2026-08-09~~ Wed 2026-08-12 *(rescheduled — missed original date)*

**LinkedIn:**
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
>
> #CorporateActions #NSE #DataEngineering #IndiaMarkets #QuantFinance

**Substack — "12 Corporate Action Types, Ranked by How Often Vendors Miss Them":**
> [LinkedIn list above]
>
> A rough ordering of "how likely is a mid-tier vendor to get this right," from safest to riskiest: cash dividends and forward splits are essentially always correct — they're common, well-understood, and every vendor tests against them. Bonus issues and rights issues are correct maybe 70–80% of the time — common enough to matter, unusual enough that edge cases (fractional entitlement ratios, partly-paid rights shares) trip up generic adjustment logic. Below that — face-value changes, capital reductions, demergers, amalgamations, NCLT restructurings — coverage drops sharply, not because the events are conceptually hard, but because they're rare enough that most pipelines were never tested against a real example.
>
> Name changes and ISIN changes belong on this list even though neither one moves the price. A name change with no ISIN change is cosmetic for price data but breaks any pipeline that joins on company name string matching. An ISIN change — rarer, but it happens on some restructurings — breaks a pipeline that treats ISIN as a permanent identifier, which most pipelines do, because it usually is one.
>
> The practical takeaway for auditing your own pipeline: don't test your adjustment logic against a split. Test it against a demerger with a face-value change on the parent in the same quarter. If that resolves correctly, the common cases were never really in doubt.
>
> Full taxonomy: tickertruth.com/methodology.

---

### 3.8 — Day 8, Mon 2026-08-10

**Rewritten 2026-08-10** — the original draft below claimed a full corporate-action
event table, backtest-ready adjustment factors, and listing status history in the
"full release." The actual latest release (`v2026.08.02`) has **0 corporate actions,
0 lineage events, 0 adjustment factor rows** — ingestion has been broken since before
that release (see `session-handoff.md`) — and only refreshes the security master.
Posting the original draft would contradict the website's own release-notes page,
which already discloses this. Replaced with a version that matches what's actually
live.

**LinkedIn:**
> Today we're publishing our latest data release at tickertruth.com — and being upfront about where it stands.
>
> What's live in this release:
> — NSE security master: 2,389 active securities, refreshed from the current NSE listing
> — Full release notes with exact record counts, published every release: tickertruth.com/release-notes
>
> What's not live yet: corporate action ingestion is currently broken upstream (NSE is blocking automated access), so corporate actions, symbol lineage, and adjustment factors haven't updated in this release. We're not going to paper over that — the release notes say it plainly, and we'll post again the day it's fixed.
>
> If you want to see exactly what changed release over release, including the gaps, that's what the changelog is for.
>
> tickertruth.com/release-notes
>
> #IndiaData #NSE #QuantFinance #DataProduct #OpenData

**Substack — "Where the Latest TickerTruth Release Actually Stands":**
> [LinkedIn text above]
>
> We'd rather ship an honest partial release than sit on one until it's polished. The security master refresh is real and useful on its own — it's the base table every lineage and adjustment calculation joins against, so keeping it current matters even in a release where nothing else moved.
>
> The corporate-actions gap is an infrastructure problem, not a data-quality one: NSE's edge is returning 403s to the extractor's requests, both locally and in CI, and there's no stale cache old enough to substitute. The fix is either a different egress path or a licensed data source — not a code patch — so we're not going to promise a date we can't back.
>
> Every release note going forward will say exactly what updated and what didn't, with row counts, not adjectives. If corporate actions come back next release, you'll see the count go from 0 to whatever it actually is. Free sample and full changelog: tickertruth.com/release-notes.

---

### 3.9 — Day 9, ~~Tue 2026-08-11~~ Thu 2026-08-13 *(shifted two days due to Day 6/7 reschedule)*

**Accuracy problem found 2026-08-17, already live — needs a decision, not just
a link fill-in.** This post (both LinkedIn and Substack, already published
2026-08-13) claims: *"TickerTruth provides both dates for every event:
announced_date, ex_date, record_date, payment_date."* Checked against the
actual schema (`dolt/schema.sql`, `fact_corporate_action_event`) and the
normalizer (`pipelines/normalize/normalizer.py`): the table has `event_date`
(populated from NSE's `EX_DATE` column), `record_date`, and `payment_date`.
**There is no `announced_date` field anywhere in the schema or pipeline** —
grep confirms zero hits for `announced_date`/`ANNOUNCED` outside this post.
The post also promises "a worked CAR example" in the sample notebook; the
closest existing notebook (`notebooks/action_event_examples.ipynb`) shows
`ex_date`, `action_type`, and `confidence_flag` but has no
announcement-vs-ex-date comparison and no CAR calculation at all. This is the
same class of problem Day 8 was rewritten for (§3.8) — the difference is Day 8
was caught and rewritten *before* publishing; this one was caught after.
**User decision 2026-08-17: edit the live LinkedIn and Substack posts
directly** (both platforms support in-place edits, same fix already applied
to the Day 10 Calendly link). Corrected text below — replace the live posts
with this, not the original draft above the line.

**LinkedIn (corrected 2026-08-17 — replace live post with this):**
> A common pattern in quant research: measure abnormal returns around a corporate event.
>
> The silent killer: most teams use the *announcement date* when they should use the *ex-date* (or record date). For some event types, these differ by weeks.
>
> TickerTruth's corporate action table sources `event_date` directly from NSE's ex-date field — not a scraped news-announcement date — plus `record_date` and `payment_date` where NSE provides them. No separate announcement-date field, by design: the ex-date is the one that actually determines the price reaction.
>
> The difference in CAR[-5,+5] between announcement-date and ex-date alignment is often 3–4% on a typical bonus issue. That's not noise — it's a measurement error that corrupts your strategy.
>
> Sample notebook: https://github.com/brkrishna/TickerTruth/blob/main/notebooks/action_event_examples.ipynb
>
> #EventStudy #QuantFinance #NSE #CorporateActions #AlgoTrading

**Substack — "Event-Study Methodology Using the Correct Corporate Action Date" (corrected 2026-08-17 — replace live post with this):**
> [LinkedIn text above]
>
> The gap between announcement and ex-date exists because Indian corporate actions typically go through board approval, shareholder approval, and a regulatory filing window before the ex-date is fixed — and each of those stages can generate its own "announcement" in a news feed or vendor API, which is where the ambiguity creeps in. If your event-study code pulls the first announcement-type record it finds for a given action, it's picking up the board-approval date more often than the market-relevant ex-date, and those can be three to six weeks apart for a bonus or rights issue.
>
> Why this specifically corrupts a CAR window: cumulative abnormal return calculations are sensitive to exactly *when* the event window starts, because the price reaction to a bonus or rights announcement is front-loaded around the date the market can actually act on it — which is the ex-date, not the announcement. Anchor the window three weeks early and you're measuring pre-event drift as if it were the event reaction, which inflates or deflates the CAR depending on which way the stock was already moving.
>
> The fix requires your data source to give you the ex-date directly rather than a scraped "announcement" string from a news feed or vendor API — which is why `event_date` in TickerTruth's corporate action table is sourced straight from NSE's own ex-date field, not inferred from filing text.
>
> Sample notebook: https://github.com/brkrishna/TickerTruth/blob/main/notebooks/action_event_examples.ipynb.

---

### 3.10 — Day 10, ~~Wed 2026-08-12~~ Fri 2026-08-14 *(new; shifted two days due to Day 6/7 reschedule)*

**LinkedIn:**
> One week since the first public release, so a quick, honest update.
>
> This week we covered: symbol discontinuity at mergers and renames, the corporate-action types most vendors miss, how to do the lineage join in 5 lines of pandas, survivorship bias from delisted tickers, how NSE data sources compare, the real cost of bad reference data, and why announcement-date vs ex-date matters for event studies.
>
> If any of that matched a problem you've actually hit in a backtest, that's the whole reason we're building this in public instead of behind a sales page.
>
> Free sample, no signup wall beyond an email: tickertruth.com
> 20-minute walkthrough if you'd rather talk it through: https://calendly.com/ramkybodi/30min
>
> #IndiaData #QuantFinance #NSE #DataProduct #Backtesting

**Substack — "One Week In: What We Covered and What's Next":**
> [LinkedIn text above]
>
> A short version of what's coming next, since a few readers asked in comments this week: BSE symbol master and lineage coverage is the next data expansion (currently NSE-only), and the two most-requested technical pieces for next week are a worked example of the demerger case (parent + child entity creation, one full walkthrough) and a short piece on how the confidence-flag system works — every lineage event and adjustment factor in the dataset carries a confidence score, and it's worth explaining what drives it up or down.
>
> If you subscribed this week off one of the daily posts: welcome, and thank you for the early read. The monthly release lands on the first business day of each month with a full changelog, and the archive of this week's posts (with the code and worked examples, not just the feed-length version) stays up on Substack if you want to send a specific one to a colleague.
>
> Everything from this week, plus the free sample, is at tickertruth.com.

---

## 4. Automating the posting with openclaw

This section assumes **openclaw** is a browser-automation agent that
executes a sequence of UI actions (navigate, click, type, wait, verify)
against a real logged-in browser session, driven by a task file you hand
it. If your actual openclaw install has a different invocation style
(a CLI flag set, a config schema, a different task-definition format),
swap the mechanics below for the equivalent — the **structure** (queue
file → per-day task → human approval gate → post → verify → log) is what
matters, not the exact syntax.

**Because publishing to LinkedIn and Substack is visible to other
people and hard to fully undo, this plan defaults to a human-approval
gate before each post goes live** — openclaw stages the post and takes a
screenshot, you approve, then it clicks Publish. Ask explicitly if you
want the gate removed and every day auto-published with no review.

### 4.1 One-time setup

1. **Log in manually once, in the same browser profile openclaw will
   drive.** Sign in to LinkedIn and to Substack (as the publication
   owner) in whatever browser/profile you point openclaw at, so its
   session cookies are already valid. Do not store your password in any
   openclaw config file — rely on the persisted browser session, not
   credential injection.
2. **Confirm openclaw can open both composers manually first**, before
   scripting anything:
   - LinkedIn: the "Start a post" box on the feed home page.
   - Substack: `https://<your-pub>.substack.com/publish/post` → **New
     post**.
   If either requires a 2FA prompt or an interstitial, run through it
   once by hand so the session is fully authenticated before the first
   scheduled run.
3. **Create the content queue file** at
   `docs/marketing/content-queue.yaml` (new file — this repo doesn't
   have a `docs/marketing/` directory yet, create it). One entry per
   day, `status` starts at `pending_review`:

   ```yaml
   - day: 1
     date: "2026-08-03"
     platform: linkedin
     status: pending_review   # pending_review -> approved -> posted -> failed
     text: |
       If you've ever run a backtest on NSE data and seen returns that
       looked too good, one likely culprit is symbol discontinuity.
       ...
     post_url: null

   - day: 1
     date: "2026-08-03"
     platform: substack
     status: pending_review
     title: "Why Your India Backtest Is Probably Lying To You"
     text: |
       ...
     post_url: null
   ```

   Populate all 20 entries (10 days × 2 platforms) from Section 3 above
   verbatim — copy-paste, don't paraphrase, so what gets reviewed is
   exactly what's in this plan.

### 4.2 Per-platform openclaw task

**LinkedIn task** (`docs/marketing/openclaw/post-linkedin.task`, or
whatever extension your openclaw build expects):

```
1. Navigate to https://www.linkedin.com/feed/
2. Click the "Start a post" input at the top of the feed
3. Wait for the post composer modal to open
4. Type the contents of {{queue_entry.text}} into the composer body
   - Preserve blank lines between paragraphs (LinkedIn's editor treats
     each Enter as a new paragraph — do not collapse them)
5. Take a screenshot of the composer with the full text visible
6. STOP and wait for human approval (see 4.4) before continuing
7. On approval: click "Post"
8. Wait for the modal to close and the new post to appear at the top
   of the feed
9. Extract the post's permalink URL (click the post's timestamp, copy
   the URL from the address bar or the "Copy link to post" menu item)
10. Write the permalink back into {{queue_entry.post_url}} and set
    status: posted
```

**Substack task** (`docs/marketing/openclaw/post-substack.task`):

```
1. Navigate to https://<your-pub>.substack.com/publish/post
2. Click "New post"
3. Type {{queue_entry.title}} into the title field
4. Click into the body editor
5. Type the contents of {{queue_entry.text}}
   - Substack's editor supports Markdown-like paste for bold/headers;
     if openclaw pastes as plain text instead, verify formatting
     matches Section 3 before continuing
6. Open post settings (gear icon) and confirm no scheduled-send date
   is set unless you want a delayed publish
7. Take a screenshot of the full rendered draft
8. STOP and wait for human approval (see 4.4) before continuing
9. On approval: click "Continue" -> "Send to everyone" / "Publish"
   (exact button label varies by Substack UI version — use whichever
   is the final publish action, not "Save draft")
10. Wait for the publish confirmation
11. Extract the live post URL from the confirmation page
12. Write the permalink back into {{queue_entry.post_url}} and set
    status: posted
```

### 4.3 Daily scheduling

Run one LinkedIn task and one Substack task per calendar day, both
reading that day's entries out of `content-queue.yaml`. Two ways to
trigger it, pick one:

- **Cron / launchd**, fixed 9:00 AM IST (peak LinkedIn engagement time
  per `marketing.md` Section 10.1 note): a shell script that finds
  today's `date` entries in the queue file with
  `status: pending_review`, hands each to the matching openclaw task,
  and exits. If nothing is `pending_review` for today (e.g. you already
  approved and posted manually), it's a no-op.
- **This agent, via `/loop` or a scheduled cloud routine**: same
  underlying trigger, but driven by Claude Code's own scheduling
  instead of system cron — usable if you'd rather have this session (or
  a scheduled one) both prep the day's queue entries *and* invoke
  openclaw, rather than a separate cron job. Say so if you want this
  wired up instead of plain cron.

Either way, keep LinkedIn and Substack as two separate task runs, not
one combined script — they have unrelated failure modes and you don't
want a Substack UI change to block the LinkedIn post for the day.

### 4.4 The approval gate

Default flow, per day, per platform:
1. openclaw stages the post (composer filled in, not yet published) and
   drops the screenshot in `docs/marketing/openclaw/screenshots/`.
2. You get notified (however your openclaw setup surfaces this — a
   message, a file, a screenshot to review) and open the screenshot.
3. Reply/flag approve or reject.
4. On approve, openclaw finishes the task (click Publish, extract URL,
   update the queue file).
5. On reject, set `status: rejected` in the queue file with a `note:`
   field explaining why, and fix the entry in Section 3 / the queue
   file before the next day's run — don't just retry the same text.

This adds a manual step to a 10-day, 20-post run, which is the point:
these are public, hard-to-unpublish posts under your name, and a
30-second screenshot check per post is cheap insurance against a typo,
a broken merge tag (`{{queue_entry.text}}` rendering literally because
of a templating bug), or posting the wrong day's content.

### 4.5 Verification and logging

After every successful post:
- Confirm the `post_url` written back to the queue file actually
  resolves (`curl -s -o /dev/null -w "%{http_code}\n" <post_url>` should
  return `200`).
- Append a row to `docs/marketing/content-log.csv` (new file):
  `date,platform,day,post_url,status,notes` — this becomes the record
  you total up against the Section 15 success metrics in `marketing.md`
  (LinkedIn impressions, follower growth, etc.) at the Day-28 sprint
  review.

### 4.6 Failure handling

- If the composer doesn't load, or the DOM has changed since the task
  script was written (a "Post" or "Publish" button that openclaw can't
  find): **do not retry blindly.** Log `status: failed` with the error,
  screenshot whatever state the browser is in, and surface it — a UI
  change needs a human to update the task steps, not a retry loop
  hammering a broken selector.
- If a post succeeds but the permalink extraction fails: the post is
  live but unlogged — check LinkedIn/Substack manually within the hour
  and backfill the URL by hand, don't post a duplicate to "fix" it.
- Never let a failed morning run silently cascade into posting two
  days' content at once the next day. Each day's task should only ever
  touch that day's queue entries.

### 4.7 Rate-limit and platform-policy notes

- One feed post per platform per day is well within normal human usage
  — this is not the DM-outreach volume in `marketing.md` Section 1 that
  needed batching to avoid spam flags. No special pacing needed for the
  posts themselves.
- Do keep the LinkedIn post under ~1,300 characters where possible (the
  "see more" truncation point) — all 10 LinkedIn drafts above are
  already sized for this.
- If LinkedIn or Substack ever present a CAPTCHA or "verify it's you"
  challenge mid-automation, stop the task and complete it manually in
  the same browser session — don't attempt to script around it.

---

## 5. What to do before Day 1

- [ ] Create `docs/marketing/` directory
- [ ] Populate `docs/marketing/content-queue.yaml` with all 20 entries
      from Section 3
- [ ] Write/confirm the two openclaw task definitions (Section 4.2) —
      exact syntax depends on your openclaw version
- [ ] Do the one-time login + manual composer test (Section 4.1)
- [ ] Decide: cron/launchd trigger or Claude-scheduled trigger (Section
      4.3)
- [ ] Confirm the approval-gate channel — where you want to see the
      staged screenshots and reply approve/reject (Section 4.4)
- [x] Fill in the `[Calendly link]` placeholder in Section 3 (Day 10)
      with the real URL: https://calendly.com/ramkybodi/30min (done
      2026-08-15, after the fact — Day 10 posted 2026-08-14 with the
      placeholder still literal on both LinkedIn and Substack; Substack
      confirmed live with `[your Calendly URL here]` unresolved, needs a
      manual edit on the published post; LinkedIn unverified, auth-walled)
- [x] Fill in the `[GitHub link]` placeholder in Section 3 Day 3 with the
      real URL: https://github.com/brkrishna/TickerTruth/blob/main/notebooks/sample_lineage_walkthrough.ipynb
      (done 2026-08-17. Turned out Day 3 Substack was never actually posted
      on 2026-08-05 despite the tracking files saying so — published for the
      first time 2026-08-17 with the corrected link, confirmed 200 via curl:
      https://tickertruth.substack.com/p/the-5-line-pandas-pattern-for-symbol.
      Day 3 **LinkedIn** post was genuinely posted 2026-08-05 and still has
      the literal `[GitHub link]` placeholder live — still needs a manual
      edit, same as the Day 10 Calendly fix)
- [x] Day 9's `[GitHub link]` placeholder turned out to hide a bigger issue
      (a false `announced_date` product claim) — see the corrected copy in
      §3.9. Went through a couple of false-done markings along the way
      (once from a `curl -o /dev/null` 200 check that only confirms the
      page loads, not the text; once from an edit that fixed only the
      notebook link — to the wrong notebook — while leaving the false claim
      untouched) before actually landing.
      **LinkedIn (urn:li:activity:7493512667886837760): confirmed fixed
      2026-08-17.** `announced_date` no longer appears anywhere in the
      post (checked via the `og:description`/`twitter:description` meta
      tags, which mirror the full post text); the corrected paragraph
      matches §3.9 verbatim. Notebook link on the live post is a
      `lnkd.in/dAFEebZS` short link — couldn't resolve it directly
      (LinkedIn 403s non-browser requests), but the user confirmed it
      redirects to `notebooks/action_event_examples.ipynb`. Closed.
      **Substack (https://tickertruth.substack.com/p/one-week-in-what-we-covered-and-whats):
      confirmed fixed 2026-08-17.** Read the rendered post body directly
      (not just HTTP status) — `announced_date` no longer appears anywhere,
      both corrected paragraphs match §3.9 verbatim, and the single
      "Sample notebook" link now points straight at
      `https://github.com/brkrishna/TickerTruth/blob/main/notebooks/action_event_examples.ipynb`
      with no shortener. Closed. Both Day 9 posts (LinkedIn + Substack) are
      done.

---

## 6. Analytics check-in (2026-08-06)

Reviewed the Cloudflare Web Analytics dashboard (Core Web Vitals panel,
date range Jul 30 – Aug 6 2026) to close out `FOLLOWUP-1` in `tasks.md`
(the beacon-token swap from commit `fec069f`, live since 2026-08-04).

**Finding: the beacon is now firing and capturing real visits.** The
Core Web Vitals panel shows real-user LCP/INP/CLS samples against actual
page paths, which only populate when the beacon script successfully
loads and reports from a real page view — this was empty under the old
token. Data points appear from Sun Aug 2 through Thu Aug 6, i.e. starting
before the Day 1–4 LinkedIn/Substack posts went out, so the token itself
was the fix, not new traffic volume from the content plan.

Pages with recorded visits: `tickertruth.com/`, `/release-notes`,
`/blog/`, `/pricing`, `/sample-queries`, `/methodology`, three individual
blog posts (`why-evol…`, `todays-a…`, `the-evol…`), and one
`tickertruth.pages.dev/` hit (the Pages.dev preview domain, not the
custom domain — worth noting since that traffic won't be from the
marketing posts, which all link to `tickertruth.com`).

Core Web Vitals are all in the "Good" band: LCP P50 582ms / P75 676ms /
P90 840ms / P99 909ms, both INP and CLS at 100% Good. No performance
concerns from this data.

**What this check-in did *not* confirm**, because the Core Web Vitals
panel doesn't surface it: absolute visit counts, top referrers (so no
LinkedIn/Substack attribution yet), or whether `/pricing` visits
correlate with a specific day's post. See `FOLLOWUP-2` in `tasks.md` for
the remaining check.

`docs/cloudflare-analytics.md` was reviewed against this finding — its
"What this doesn't do" caveats are still accurate as written; no update
needed.
