# Google Search Console Setup

How to verify tickertruth.com with Google and submit the sitemap so pages get indexed.

---

## Step 1 — Sign in to Google Search Console

Go to [search.google.com/search-console](https://search.google.com/search-console) and sign in with your Google account.

---

## Step 2 — Add tickertruth.com as a Property

1. Click **"Start now"** or the **"+ Add property"** dropdown in the top-left sidebar
2. Choose **"Domain"** (not "URL prefix")
   - Domain: `tickertruth.com`
   - This covers http, https, www and non-www all in one property
3. Click **Continue**

---

## Step 3 — Verify ownership via DNS

1. Google shows you a **TXT record** — looks like: `google-site-verification=abc123xyz...`
2. Go to your DNS provider (Cloudflare, GoDaddy, Namecheap, etc.)
3. Add a new **TXT record**:
   - **Name/Host**: `@` (root domain)
   - **Value**: paste the full `google-site-verification=...` string
   - **TTL**: Auto or 3600
4. Save, then return to Search Console and click **Verify**
5. DNS propagates in a few minutes to a few hours — if it fails immediately, wait 15 min and retry

> **Cloudflare note:** Set the TXT record proxy status to **DNS only** (grey cloud), not proxied.

---

## Step 4 — Submit the sitemap

1. In the left sidebar click **Sitemaps** (under "Indexing")
2. In the "Add a new sitemap" box type: `sitemap.xml`
   - Full URL: `https://tickertruth.com/sitemap.xml`
3. Click **Submit**
4. Status should show **"Success"** with 6 URLs found

---

## Step 5 — Request indexing for the homepage

1. Click the **search bar at the top** of Search Console ("Inspect any URL in...")
2. Type: `https://tickertruth.com/`
3. Click **"Request Indexing"**
4. Repeat for other pages if desired (pricing, methodology, sample-queries, release-notes, contact)

---

## What to expect

| Timeframe | What happens |
|---|---|
| 0–24 hours | Google crawls the homepage |
| 1–3 days | Pages appear in the Coverage report |
| 1–2 weeks | Pages start showing in search results |
| 2–4 weeks | Rankings stabilise |

Check the **Coverage** report after 3–4 days to confirm all 6 pages are indexed. Any errors (404s, redirect issues, blocked by robots.txt) will appear there.
