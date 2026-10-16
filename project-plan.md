# Project plan

## Issues

### Summary

**5 of 15 done** · `███████░░░░░░░░░░░░░` 33% · 🔴 0 overdue · 🟡 4 due within 7 days · ⚪ 6 later

| Area | Open | Done |
|------|------|------|
| infra | 3 | 3 |
| security | 5 | 1 |
| email | 2 | 1 |

### Open

#### 🟡 Due within 7 days

| id | area | description | due_date |
|----|------|-------------|----------|
| 6 | email | Change the Email Routing catch-all on tickertruth.com from forward to drop (Email > Email Routing > Routing rules; currently all -> forward) so random local-parts stop reaching the inbox (spam floods, address harvesting); named rules today: connect@tickertruth.com only; add a named rule first for any published address that is not listed | 2026-10-16 |
| 3 | infra | Switch SSL/TLS encryption mode on tickertruth.com from Full to Full (strict) (SSL/TLS > Overview; API setting ssl=full) - Full accepts a self-signed origin certificate; the site is served by a Worker with no external origin so strict has no downside; verify the site and webhook endpoints still respond afterwards | 2026-10-20 |
| 9 | security | Re-run Security Center scan for tickertruth.com and dismiss the stale Security.txt not configured finding - https://tickertruth.com/.well-known/security.txt already returns 200 with Contact connect@tickertruth.com and Expires 2027-08-23; if it persists add Policy and Encryption fields | 2026-10-20 |
| 10 | security | Verify Bot Fight Mode (on) and AI bot blocking (ai_bots_protection=block, crawler_protection=enabled) on tickertruth.com do not challenge the Razorpay webhook to /api/razorpay-webhook or Resend callbacks - trigger a Razorpay test event and confirm 200; this is the only zone with Bot Fight Mode enabled | 2026-10-20 |

#### ⚪ Later

| id | area | description | due_date |
|----|------|-------------|----------|
| 4 | infra | 🧑 Enable DNSSEC on tickertruth.com (DNS > Settings > DNSSEC; currently disabled) and add the DS record it shows at the domain registrar (automatic only if the domain is registered at Cloudflare); verify with `dig DS tickertruth.com +short` and dnsviz.net, then confirm email routing and Resend verification still resolve | 2026-10-27 |
| 11 | security | Add a reporting endpoint (report-uri / Reporting-Endpoints) to the Content-Security-Policy-Report-Only header in the Transform Rule Baseline security headers - tickertruth.com (Rules > Transform Rules > Modify Response Header) - the policy is report-only with no endpoint so violations are never collected; review reports for 1-2 weeks before enforcing | 2026-10-27 |
| 12 | security | Enforce CSP on tickertruth.com: rename Content-Security-Policy-Report-Only to Content-Security-Policy in the Baseline security headers transform rule and replace 'unsafe-inline' in script-src and style-src with hashes or nonces (pages use inline style/script blocks), then check every page and the Turnstile widget for console CSP errors | 2026-11-13 |
| 13 | security | Raise HSTS on tickertruth.com from max-age=15552000 (180 days, includeSubDomains, no preload) to max-age=31536000; includeSubDomains; preload in the Baseline security headers transform rule once every subdomain is HTTPS-only, then submit tickertruth.com at hstspreload.org; Cloudflare-side HSTS (SSL/TLS > Edge Certificates) is disabled so the transform rule is the only source | 2026-11-13 |
| 14 | infra | Add CAA records on tickertruth.com (none today) limiting certificate issuance to the CAs Cloudflare Universal SSL uses plus an iodef mailto - copy the current CA list from Cloudflare docs first so renewals are not blocked (certs expire 2026-11-20 / 2026-11-30 on truesignal.company, check each zone) and watch Edge Certificates for renewal after the change | 2026-11-13 |
| 15 | email | Review DMARC aggregate reports arriving at brkrishna@gmail.com for tickertruth.com (p=none since 2026-10-16) after 2-4 weeks; if legitimate senders (Resend/SES send.tickertruth.com, Cloudflare Email Routing) all pass SPF/DKIM alignment, raise the _dmarc record to p=quarantine, then later p=reject (DNS > Records, edit _dmarc TXT) | 2026-11-13 |

### Completed

| id | area | description | due_date |
|----|------|-------------|----------|
| 1 | infra | Turned on Always Use HTTPS for tickertruth.com (done 2026-10-16, `curl -I http://tickertruth.com/` now 301) (SSL/TLS > Edge Certificates; always_use_https is off) - `curl -I http://tickertruth.com/` currently returns 200 over plain HTTP so pages and the contact form can be loaded and submitted unencrypted before HSTS is learned; after the change expect a 301 to https://tickertruth.com/ and re-run smoke-test | 2026-10-16 |
| 2 | infra | Raised Minimum TLS Version on tickertruth.com to 1.2 (done 2026-10-16; `openssl s_client -tls1_1 -cipher 'ALL:@SECLEVEL=0'` now gets `alert protocol version`, TLS 1.2 handshake and https site still 200) - Raise Minimum TLS Version on tickertruth.com from 1.0 to 1.2 (dashboard SSL/TLS > Edge Certificates; API setting min_tls_version is the default 1.0 today, so TLS 1.0/1.1 clients are still accepted although TLS 1.3 is on); verify afterwards that `openssl s_client -connect tickertruth.com:443 -tls1_1` fails and the site and /api/contact still work | 2026-10-16 |
| 5 | email | Added DMARC TXT at _dmarc.tickertruth.com (done 2026-10-16 via DNS > Settings > Email Security wizard; `dig TXT _dmarc.tickertruth.com +short` returns `v=DMARC1; p=none; rua=mailto:brkrishna@gmail.com`; reports go to the account Gmail by choice) - Add a DMARC TXT record at _dmarc.tickertruth.com (none exists - Security Insights flags DMARC Record Error for tickertruth.com and send.tickertruth.com) starting with `v=DMARC1; p=none; rua=mailto:<Cloudflare DMARC Management address>` via DNS > Settings > Email Security; review aggregate reports for 2-4 weeks, then raise to p=quarantine and p=reject (the send.tickertruth.com Resend/SES subdomain inherits the org-domain policy) | 2026-10-16 |
| 7 | security | Rate limiting deployed (done 2026-10-16, commit 24f044f; CONTACT_RATE_LIMITER 5/60s and WEBHOOK_RATE_LIMITER 30/60s bound on the live Worker; bursts against tickertruth.com returned 429 on /api/contact (16 of 100) and /api/razorpay-webhook (1 of 200) - Cloudflare's limiter is per-location and approximate, so it trips under sustained bursts rather than at exactly the limit; unit tests cover the 429 path) - Add rate limiting to POST /api/contact in src/index.js (also /api/razorpay-webhook: keep signature check, rate-limit unauthenticated hits) with a Workers Rate Limiting binding (ratelimits block in wrangler.jsonc, same as answerkept CONTACT_RATE_LIMITER limit 5 per 60s keyed on client IP), return 429 when exceeded and add a test - no ratelimits binding and no zone rate-limiting rule exists, so a bot holding valid Turnstile tokens can flood Resend sends and burn quota | 2026-10-16 |
| 8 | infra | Disabled workers.dev and preview URLs (done 2026-10-16; https://tickertruth.brkrishna.workers.dev now 404) - Disable the public workers.dev route for Worker tickertruth - add workers_dev:false and preview_urls:false to wrangler.jsonc (both enabled today; https://tickertruth.brkrishna.workers.dev returns 200 with the full site and serves none of the zone security headers, Bot Fight Mode, rate limiting or redirects of tickertruth.com); if preview URLs are needed to validate non-main pushes keep them but put them behind Cloudflare Access | 2026-10-16 |
