# Cloudflare Web Analytics

How visit tracking works on tickertruth.com, where to find the dashboard,
what each metric means, and how to read it against the site's actual goals
(SEO indexing, blog reach, pricing-page intent).

## What's actually running

The site uses **Cloudflare Web Analytics** — a lightweight JS beacon, not
Google Analytics. There is no GA4 tag anywhere on the site (a deliberate
choice; see "What this doesn't do" below).

The beacon is a single script tag with a site-specific token:

```html
<script defer src="https://static.cloudflareinsights.com/beacon.min.js"
        data-cf-beacon='{"token": "4cf86be656924547a93bfba532bc23bc"}'></script>
```

It's embedded in two places, both using the same token so all traffic
counts against one dashboard:

| Where | File |
|---|---|
| The 6 landing pages | `website/landing-page/index.html`, `pricing.html`, `methodology.html`, `sample-queries.html`, `release-notes.html`, `contact.html` |
| Every blog page | `website/blog/layouts/partials/footer.html` (Hugo partial, renders site-wide) |

The blog placement is recent — until it was added, blog traffic wasn't
tracked at all. If you're comparing before/after numbers, treat anything
before that change as landing-page-only data.

## Where to find the dashboard

Web Analytics is its own product, not nested inside the Pages project:

1. [dash.cloudflare.com](https://dash.cloudflare.com) → select the account
2. Left sidebar → **Analytics & Logs** → **Web Analytics**
3. Click into the `tickertruth.com` site (identified by the token above)

This is a different screen from the Pages project's own **Analytics** tab
(which shows deploy/build/request-serving stats — infrastructure metrics,
not visitor behavior). Both exist; they answer different questions.

## What each metric means

| Metric | What it counts |
|---|---|
| **Visits** | A visit session — one visitor, grouped by a time-boxed window (not cookie-based; Cloudflare uses a privacy-preserving heuristic, not a persistent visitor ID) |
| **Page views** | Every page load that fired the beacon script |
| **Top paths** | Which URLs got the most views — this is the one to watch for "did people actually reach `/pricing`" |
| **Top referrers** | Where visits came from: direct, a search engine, LinkedIn, Substack, etc. |
| **Top countries** | Visitor geography (coarse, IP-based) |
| **Top browsers / OS / device types** | Standard user-agent breakdown |
| **Core Web Vitals** (a separate panel) | Real-user LCP / CLS / INP samples from actual visitor page loads, not a lab test — useful for confirming the site feels fast for real people, not just in Lighthouse |

There's no bounce rate, session duration, or funnel/goal tracking — Cloudflare
Web Analytics deliberately doesn't compute those, since they usually require
persistent identifiers it's designed to avoid.

## Reading it against what actually matters here

Given the current goals (get the blog indexed, drive traffic from the
10-day content plan in `docs/marketing-plan.md`, and eventually convert to
`/pricing`), the metrics worth checking regularly are:

- **Top referrers, filtered to LinkedIn / Substack** — confirms whether a
  given day's post in the content plan actually drove clicks, not just
  impressions on the platform itself.
- **Top paths including `/pricing`** — visits to `/pricing` are the closest
  proxy this dashboard has to purchase intent. A spike here after a specific
  blog post or LinkedIn post is a signal that post worked.
- **Page views on `/blog/posts/*`** — now that the beacon covers blog pages,
  this tells you which posts are actually getting read versus just indexed.
- **Visits over time, cross-referenced with the Search Console "Discovered"
  → "Indexed" transition** (see `docs/google-search-console-setup.md`) — once
  pages move to indexed, visits from organic search should start appearing
  under "Top referrers" as a search engine rather than staying at zero.

## What this doesn't do

- **No user-level tracking, no cookies, no cross-session identity** — by
  design. This is why it doesn't need a cookie consent banner.
- **No conversion/goal tracking** — it can't tell you someone who viewed
  `/pricing` later paid. That link has to be made manually (e.g., cross-referencing
  a payment against the date/traffic spike).
- **No session recording or click-level detail.**
- **Ad blockers and privacy extensions that block `cloudflareinsights.com`
  suppress the beacon** — real traffic is very likely undercounted by some
  margin, more so among technically sophisticated visitors (quant researchers,
  data engineers — exactly this site's audience), who are more likely to run
  such tools. Treat the numbers as a directional floor, not an exact count.

If any of this becomes a real blocker — needing actual conversion tracking,
funnels, or audience segments — that's the point to revisit adding GA4
(deliberately skipped for now in favor of not needing a cookie banner).
