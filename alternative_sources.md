# Alternative sources for 15-min-delayed NSE quote data

Research only — no code changes. Context: `pipelines/extract/` currently pulls
NSE equity master, EOD bhavcopy, and corporate actions, all end-of-day. The
question here is whether to add intraday (~15-min-delayed) quotes, and if so,
from where. TickerTruth is a **commercial** product (paid tiers, buyer
registry, signed R2 URLs — see `pipelines/publish/`), which changes the
calculus versus a personal/research project: redistribution rights matter as
much as technical feasibility.

## TL;DR recommendation

Don't scrape NSE's own site or Yahoo Finance for a paid product — both carry
real ToS/legal exposure the moment quote data reaches a paying customer. The
two viable paths are:

1. **Cheapest legitimate path**: a broker API (Zerodha Kite Connect, ₹500/mo)
   for internal/prototype use only — not resellable to customers, but fine if
   the goal is to validate demand or build an internal dashboard first.
2. **Actual product path**: an NSE-authorized data vendor (TrueData or Global
   Datafeeds) or NSE's own official 15-min-delayed feed (NIBIS) — both are
   licensed for redistribution, at real but bounded cost (~₹90,000/yr +
   vendor markup, or vendor subscription plans).

Everything free (yfinance, nsetools, jugaad-data, scraping nseindia.com
directly) is either personal-use-only by ToS, technically unstable, or both.
None of them should sit underneath a paid feature.

---

## Requirements to keep in mind

- **Redistribution**, not just consumption — customers ultimately see this
  data, so "can I fetch it" is a different (and easier) question than "can I
  sell it."
- **Coverage** — ideally whole-market or whole-index snapshots (not one HTTP
  call per symbol × ~2,400 symbols).
- **Stability** — this pipeline already leans on NSE's undocumented `www.
  nseindia.com` APIs for corp actions with a Playwright fallback; adding a
  second fragile undocumented dependency compounds operational risk.
- **Cost proportionate to what this feature earns** — this is a reference-data
  product, not a trading system; sub-second latency is not a requirement, so
  premium real-time feeds are overkill.

---

## Options evaluated

### 1. yfinance (Yahoo Finance)

- **What**: Python wrapper around Yahoo Finance's unofficial endpoints.
  NSE symbols map via `.NS` suffix (e.g. `RELIANCE.NS`).
- **Coverage**: broad — most NSE-listed equities are mirrored on Yahoo.
- **Delay**: informally close to real-time/delayed for NSE tickers, but Yahoo
  does not publish or guarantee a specific delay figure.
- **Cost**: free.
- **Reliability**: no documented rate limits, no SLA — Yahoo can and does
  change endpoint shape or block scraping traffic without notice. Multiple
  2026 sources note it "relies on unofficial endpoints that can rate-limit or
  break without notice."
- **Legal**: Yahoo's Developer API Terms of Use state the API is intended for
  **personal use only**; yfinance's own docs point back to Yahoo's ToS and
  disclaim any affiliation. Using it as the data source behind a paid tier is
  a direct ToS conflict, not a gray area.
- **Verdict**: fine for internal prototyping/backtesting, **not viable** as
  the source for anything customers pay for.

### 2. jugaad-data / nsetools / nsepython (NSE scraping wrappers)

- **What**: community libraries that scrape or call `nseindia.com`'s public
  pages/APIs directly (same domain this repo already touches for corp
  actions). `jugaad-data` is the most actively maintained in 2026 and
  specifically targets NSE's current site structure; `nsetools` is older and
  more likely to break.
- **Coverage**: live quotes, indices, historical — good breadth.
  **Delay**: effectively real-time when it works (same feed the NSE website
  itself uses), not a stable "15-min delayed" product — it can be blocked
  entirely by the same Akamai bot-mitigation this project already fights in
  `extractor.py` (confirmed in the earlier experiment: intermittent 403s and
  a 404 that looks like soft-blocking).
- **Cost**: free.
- **Reliability**: inherits all the fragility already documented in
  `pipelines/extract/CLAUDE.md` for this exact domain — Akamai challenges,
  IP-reputation blocks, endpoint churn. This is not a new risk, just the same
  one applied to a second endpoint.
- **Legal**: scraping `nseindia.com`'s live data and reselling it violates
  NSE's own terms (this is precisely what the official 15-min feed and the
  "Authorized Realtime Data Vendors" program exist to license). Same problem
  as yfinance, arguably worse since it's the exchange's own paywalled data.
- **Verdict**: not viable for the product; could still be useful as a
  free/no-signup way to sanity-check numbers coming from a licensed feed
  during development.

### 3. Broker APIs (Zerodha Kite Connect, Upstox, Angel One SmartAPI, Fyers)

- **What**: Indian stockbroker trading APIs that also expose market data,
  aimed at retail algo-traders.
- **Cost (2026)**: Zerodha Kite Connect — free tier has no market data;
  ₹500/mo per API key unlocks live + historical data. Upstox, Angel One
  SmartAPI, and Fyers each offer free API access for their own account
  holders.
- **Coverage/delay**: live (not just 15-min-delayed) tick data for NSE/BSE —
  more than what's needed here.
- **Legal**: these are built for the API holder's own trading/analysis use
  under their brokerage agreement — none of them license the data for
  redistribution to third parties. Standing up "buy a Kite Connect key and
  pipe it into a product other people pay for" is the same redistribution
  problem as above, just wrapped in a broker relationship instead of a
  scraper.
- **Verdict**: cheap and reliable for internal use (e.g., validating pipeline
  output against a live source, building an internal dashboard) — not a
  licensed path to resell.

### 4. NSE-authorized data vendors (TrueData, Global Datafeeds, and similar)

- **What**: companies formally licensed by NSE ("Authorized Realtime Data
  Vendors") to redistribute NSE market data, including delayed/real-time
  feeds, via their own APIs.
- **Coverage**: NSE EQ/F&O/Indices, BSE, MCX — broad, whole-market feeds.
- **Cost**: subscription-based; both vendors gate exact pricing behind signup
  (SEBI-mandated PAN verification before showing rate cards), so an exact
  number needs a direct inquiry, but the market segment (retail algo traders)
  suggests this is priced well under the ₹90,000/yr official NSE tariff below
  — it's the whole reason these vendors exist.
- **Legal**: this is the point of the product — resale rights are baked into
  their NSE authorization.
- **Verdict**: **the most practical route to a legally resellable feed** if
  the goal is genuinely a licensed 15-min product rather than a prototype.
  Needs a direct pricing conversation with TrueData/Global Datafeeds before
  committing.

### 5. NSE's own official 15-min-delayed feed (NIBIS)

- **What**: NSE Data & Analytics Ltd's own delayed-snapshot product,
  documented in `Snapshot_15_CM.pdf` (fetched and reviewed during this
  research). Delivered as binary `.mkt`/`.ind`/`.ca1` files over **SFTP**
  (not REST/JSON), regenerated every 1 minute with a 15-minute-old snapshot,
  one file per interval, keyed by a numeric security token resolved via a
  `securities.dat` master file. Requires an SSH keypair exchange and a
  signed agreement with NSE Data & Analytics before they issue SFTP
  credentials.
- **Cost** (from the official tariff PDF, `Download 15 mins delayed data
  tariff.pdf`): **₹90,000/year for Capital Market** (also ₹90,000 for F&O,
  ₹60,000 for Currency Derivatives/WDM), charged **per medium of display** —
  website and mobile app count as two separate mediums and are billed
  separately. International pricing is $6,000/yr (CM/F&O) or $2,500/yr
  (CD/WDM).
- **Legal**: this is the actual license. Note explicitly in the tariff sheet:
  *"if delayed data... is provided in the form of data feeds to vendor's
  clients for any type of usage, written consent from NSE Data & Analytics is
  mandatory"* — so even after paying for this feed, redistributing it to
  TickerTruth's own customers likely needs a separate written sign-off from
  NSE, not just the base subscription.
- **Engineering cost**: nontrivial relative to the rest of this pipeline —
  a binary protocol parser (fixed-width structs per the field tables in the
  PDF: Security Token, LTP, best bid/ask, OHLC, all as packed shorts/longs),
  an SFTP poller running on a 1-minute cadence, and token↔symbol resolution
  via `securities.dat`. This is a different engineering shape than every
  other extractor in this repo (all HTTP/CSV/JSON today).
- **Verdict**: the gold-standard, fully-licensed option, but it's a genuine
  project on its own — new protocol, new infra (persistent SFTP polling),
  ~₹90,000+/yr, and a follow-up redistribution approval from NSE. Only worth
  it once there's validated customer demand for intraday data specifically.

### 6. Global aggregator APIs (Alpha Vantage, Twelve Data, EODHD, Polygon.io)

- **What**: multi-exchange market data APIs aimed at developers; several
  advertise 15-min-delayed free tiers.
- **Coverage**: strong for US markets; **NSE/India equity coverage depth is
  unclear** — none of the vendor docs surfaced in this research confirm
  specific NSE symbol coverage or delay guarantees for Indian equities
  specifically (most of their delayed-data marketing is US-market-focused,
  since delayed US data is a regulated product under FINRA/SEC rules).
  Would need a direct check of each vendor's symbol/exchange list for `NSE`
  before considering further.
- **Verdict**: worth a 15-minute coverage check if the licensed-vendor route
  (option 4) turns out to be more expensive than expected, but not
  independently researched further here since India coverage looks thin.

---

## Legal thread running through all of this

The one finding that should drive the decision more than any technical
detail: **every free/scraped source here is personal-use-only by its own
terms**, and this product already sells data to buyers. That's not a
theoretical risk — it's the exact reason NSE runs both an official paid feed
*and* an "Authorized Realtime Data Vendor" licensing program: the raw feed is
commercially licensed, full stop. Whichever direction this goes, the feed
underneath a paid TickerTruth tier needs to be one where redistribution is
explicitly licensed (options 4 or 5), not one where it's merely undetected.

## Suggested next step

Given the cost and integration effort of both licensed options, the cheapest
way to de-risk this is a **paid-tier demand check first**: is there evidence
existing/prospective buyers actually want intraday quotes, versus the
EOD/corporate-actions/lineage data this product already sells? If yes, get an
actual quote from TrueData or Global Datafeeds (option 4) — likely faster to
integrate (REST/WebSocket APIs, not raw binary SFTP) and probably cheaper
than NSE's direct ₹90,000/yr-per-medium NIBIS feed. Only pursue the direct
NIBIS feed (option 5) if vendor pricing turns out to be worse, or if
white-label/no-middleman terms matter for some other reason.
