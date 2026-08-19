# Outreach CRM Setup

Covers `marketing.md` §18 Phase 1 — Airtable CRM + target list. 20 Tier
1–3 companies are pre-populated in `outreach-crm.csv`; names, LinkedIn
URLs, and Tier 4 contacts still need manual research (see §3).

---

## 1. Import into Airtable

1. Create a free Airtable base named "TickerTruth Outreach CRM".
2. Create a table, import `docs/marketing/outreach-crm.csv` directly
   (Airtable's CSV import maps columns automatically).
3. After import, change these field types (Airtable defaults everything
   to single-line text on CSV import):
   - `Tier` → Single select (options: 1, 2, 3, 4)
   - `LinkedIn URL` → URL
   - `Email` → Email
   - `Touch 1 Date`, `Touch 2 Date`, `Touch 3 Date` → Date
   - `Template Used` → Single select (options: A, B, C, D, E)
   - `Status` → Single select (options: Prospect, Contacted, Replied,
     Demo Booked, Trial Sent, Negotiating, Paid, Dead, Dormant)

## 2. Views to Create

- **"Sprint Week 1 — Batch 1"** — filter `Tier = 1`, sort by `Status`.
- **"Follow-up Due"** — filter `Touch 1 Date ≤ TODAY() - 4` AND
  `Status = Contacted`.
- **"Active Leads"** — filter `Status` is any of {Replied, Demo Booked,
  Trial Sent, Negotiating}.

## 3. Filling In Names and LinkedIn URLs

Not pre-filled — verifying who currently holds a "Head of Quant" or
"Head of Data" role at a specific fund requires a live LinkedIn search;
guessing or reusing a stale name risks emailing the wrong person or a
former employee, which is worse than no contact at all.

For each of the 20 rows: LinkedIn search `"<Company>" quant` or
`"<Company>" data` or `"<Company>" research`, per the `Notes` column hint
already in the CSV. Budget ~15 min/company (per `marketing.md` §18
Phase 1). Fill in `Name` and `LinkedIn URL`; leave `Email` blank unless
it's public — cold email uses Template D only when you already have one.

## 4. Tier 4 — Indie Quants (20 contacts, not in the CSV yet)

Tier 4 isn't a named-company list — it's sourced live: LinkedIn search
"algorithmic trading India NSE" filtered to posts in the last 30 days,
plus QuantInsti EPAT alumni posting about Python/backtesting. Add rows
to the CRM as you find them, `Tier = 4`, `Company` = their firm or
"Independent". Target 20 for Batch 4 (Day 21 per the sprint calendar in
`marketing.md` §11).

## 5. LinkedIn Profile Prep (do before Touch 1 on any contact)

Per `marketing.md` §18 Phase 1:
- Update headline: "Building TickerTruth — versioned NSE + BSE reference
  data for quant teams and fintech data engineers"
- Update About section: lead with the pain, then product, then Calendly
  CTA (https://calendly.com/ramkybodi/30min)
- Add tickertruth.com to Contact Info
- **Connect with every Tier 1/2 prospect at least 48 hours before the
  first DM** — a connection request and a DM in the same moment reads as
  automated.

## 6. Next Action

Once names are filled in for Tier 1 (8 companies): send Batch 1 using
Template A (`marketing.md` §7), 5–7 DMs per session across 3 sessions in
a day, not all 20 at once (LinkedIn spam-flags rapid-fire DMing). Log
`Touch 1 Date` and set `Status = Contacted` for each as you go.

## 7. Status (2026-08-19) — paused, resume week of 2026-08-25

Tried using public web search/fetch (not LinkedIn) to pre-fill Tier 1
names ahead of the manual pass in §3. Result: 1 of 3 companies attempted
worked cleanly —

- **Marcellus Investment Managers** — filled in: Krishnan V R, Head of
  Quantitative Research (found via marcellus.in/our-team/, LinkedIn URL
  cross-checked via search). Still needs a live LinkedIn check before
  Touch 1 to confirm he's still current, same as any other row.
- **White Oak Capital** — team page blocks non-browser fetches (403);
  general web search only surfaces the founder, not a quant/systematic
  lead. Not filled in.
- **Quantum AMC** — general web search surfaces MD/CIO-level names only,
  not the quant/research-desk person the role hint is looking for. Not
  filled in.

Remaining Tier 1 rows (DSP Quant Fund, Nippon India Quant, Edelweiss
AIF, Axis AMC, Motilal Oswal AMC) not attempted. Takeaway: public search
has a low hit rate for this (~1 in 3, and every hit still needs manual
LinkedIn confirmation per §3) — the direct LinkedIn search in §3 is
likely faster for the rest. User is picking this back up the week of
2026-08-25.
