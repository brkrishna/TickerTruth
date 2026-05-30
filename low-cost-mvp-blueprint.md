# Zero-to-low-cost MVP blueprint for the India corporate-actions and symbol-history truth layer

This blueprint is designed for a low-risk side-hustle launch using your preferred Python-led stack and a low-cost hosting model before any move to Snowflake or Databricks.[cite:20][cite:208] It assumes the goal is to validate demand cheaply, sell early subscriptions manually, and only upgrade infrastructure after seeing customer pull.[web:224][web:214][web:217]

## 1. Core strategy

Do not start with a warehouse marketplace. Start with a **versioned reference-data product** plus a simple commercial wrapper. The cheapest credible stack for this use case is:

- Python pipelines for extraction and normalization.[cite:20]
- Dolt or DoltHub for versioned tabular truth data and change tracking.[web:217][web:223]
- Cloudflare Pages for a public landing page and product docs.[web:224]
- Cloudflare R2 for downloadable CSV/Parquet snapshots because R2 advertises zero egress fees and low-cost object storage.[web:214][web:215]
- Optional Hugging Face dataset mirror for discoverability and sample data distribution.[web:216][web:219]

This gives you a product that is real enough to buy, but cheap enough to shut down if interest is weak.[web:214][web:217][web:224]

## 2. MVP product definition

### Product name

**India Symbol History and Corporate Actions Truth Layer**

### What the MVP includes

- Current and historical symbol lineage for NSE-listed equities.
- Normalized corporate-action event table.
- Adjustment factors for backtesting and analytics.
- Security master with active/inactive status.
- Release notes and version history.
- Sample SQL and CSV/Parquet bundles.[cite:18][cite:208]

### What the MVP excludes

- Full exchange-level real-time data.
- Deep BSE coverage in version 1.
- Full institutional SLA commitments.
- API-first delivery at launch.
- Marketplace-native billing in phase 1.

## 3. Recommended repo and project structure

Use a mono-repo with product, data, and website components separated clearly.

```text
india-symbol-truth-layer/
├── README.md
├── docs/
│   ├── product-overview.md
│   ├── methodology.md
│   ├── release-notes.md
│   ├── pricing.md
│   └── sample-queries.md
├── data/
│   ├── raw/
│   ├── staging/
│   ├── curated/
│   └── samples/
├── pipelines/
│   ├── extract/
│   ├── normalize/
│   ├── lineage/
│   ├── adjustments/
│   └── publish/
├── dolt/
│   ├── schema.sql
│   ├── seed/
│   └── migration/
├── website/
│   ├── landing-page/
│   └── assets/
├── notebooks/
│   ├── sample_lineage_walkthrough.ipynb
│   ├── action_event_examples.ipynb
│   └── adjusted_vs_raw_series.ipynb
└── releases/
    ├── monthly/
    └── changelogs/
```

This structure supports public docs, private processing, sample releases, and future migration to Snowflake or Databricks.[cite:20][web:217][web:224]

## 4. Core tables for the MVP

### Dimensions

- `dim_security_master`
- `dim_issuer`
- `dim_exchange`
- `dim_symbol_alias`
- `dim_corporate_action_type`

### Facts

- `fact_equity_eod`
- `fact_corporate_action_event`
- `fact_adjustment_factor`
- `fact_symbol_lineage_event`
- `fact_listing_status_history`

### Public sample views

- `vw_security_current`
- `vw_symbol_lineage_sample`
- `vw_action_timeline_sample`
- `vw_adjusted_price_reference_sample`

### Paid views / files

- Full lineage history.
- Full adjustment history.
- Full action taxonomy and provenance flags.
- Full backtest-ready map tables.[cite:18][cite:23][cite:208]

## 5. Delivery model before marketplaces

### Manual subscription model

Before Snowflake or Databricks, sell access in one of four simple ways:

1. Monthly CSV/Parquet package delivered through private R2 links.
2. Private DoltHub repo access for subscribers.[web:223][web:217]
3. Password-protected download portal on Cloudflare Pages plus R2-backed asset links.[web:224][web:214]
4. Email-based release distribution plus invoice/UPI/Stripe payment collection handled manually.

This is intentionally simple. The first goal is not automation; it is willingness to pay.[web:214][web:224]

## 6. Release workflow

### Weekly internal workflow

1. Pull new NSE archives and action pages.[web:144][web:156]
2. Run normalization and lineage rules.
3. Compute new adjustment factors.
4. Run QA checks and conflict reports.
5. Update Dolt tables and commit the new version.[web:217]
6. Export public sample files and paid release files.
7. Publish updated changelog and release notes.
8. Upload release bundles to R2.[web:214][web:215]

### Monthly commercial workflow

1. Freeze the monthly release.
2. Publish public sample updates.
3. Send subscriber update email with release highlights.
4. Invoice new and renewing customers.
5. Collect feedback and backlog missing symbols/events.

## 7. Suggested tooling choices

### Lowest-cost version

- Local Python scripts + cron or lightweight Airflow on your own machine.[cite:20]
- GitHub repository for code and docs.
- Cloudflare Pages free tier for the site.[web:224]
- Cloudflare R2 for release artifacts.[web:214]
- Public DoltHub repo or local Dolt for versioning.[web:217][web:223]

### Slightly more robust version

- Small VPS for scheduled jobs.
- GitHub Actions for parts of the release workflow.
- Private DoltHub repository for paid customer access.
- Domain email and Stripe/Gumroad/Lemon Squeezy for payment and receipts.

## 8. Launch plan

### Phase 0: prep, week 1

- Finalize positioning and buyer persona.
- Build landing page copy.
- Publish methodology and sample schema.
- Prepare a small free sample release.[cite:18][cite:208][web:224]

### Phase 1: soft launch, weeks 2–3

- Launch website and sample dataset.
- Publish 2 technical posts on LinkedIn explaining symbol lineage and adjustment problems in India datasets.
- Reach out to 20–30 target buyers directly.
- Offer 3 design-partner slots with discounted pricing for feedback rights.[cite:18][cite:24]

### Phase 2: first paid pilots, weeks 4–8

- Convert 1–3 design partners.
- Run monthly releases manually.
- Improve docs based on buyer questions.
- Add one standout feature such as event-confidence scoring or a “broken vs corrected backtest” example.

### Phase 3: scale test, months 3–4

- Push more outreach to fintech product teams, quant boutiques, and broker research teams.
- Add a paid richer tier.
- Decide whether to stay manual longer or move to marketplace delivery.[web:85][web:86]

## 9. Promotion plan

### Best promotion channels

- LinkedIn posts and direct messages to heads of data, quants, and fintech CTOs.
- India capital-markets communities and finance engineering groups.
- GitHub repo with excellent docs and release notes.
- Technical blog posts comparing naïve vs corrected historical series.
- Short demo videos or notebook walkthroughs.

### Content themes that can attract buyers

- “Why India backtests break when ticker history is wrong.”
- “Corporate actions are not just dividends and splits — here is what most teams miss.”
- “How to build survivorship-aware India equity analytics.”[cite:18][cite:23]

### Promotion rhythm

- 2 educational posts per week.
- 10 direct outreaches per week.
- 1 product update / changelog post per month.
- 1 sample notebook or walkthrough every month.

## 10. Pricing and revenue model

### Suggested early pricing

| Plan | What buyer gets | Indicative monthly price |
|---|---|---|
| Explorer | Limited sample/history, delayed updates | Free or nominal |
| Starter | Core lineage and action tables, monthly release | INR 15,000 to 35,000 |
| Professional | Full history, adjustment factors, QA flags, better support | INR 40,000 to 1,00,000 |
| Enterprise | Custom coverage, dedicated support, BSE add-ons, bespoke exports | INR 1.5 lakh+ |

### Why this can work

This is not priced as raw data volume. It is priced as a trust layer that saves research errors, engineering cleanup time, and broken analytics pipelines.[cite:18][cite:23]

## 11. Potential revenue scenarios

### Conservative scenario by month 6

- 2 Starter customers at INR 20,000/month.
- 1 Professional customer at INR 50,000/month.
- Monthly recurring revenue: INR 90,000.
- Annualized run rate: INR 10.8 lakh.

### Moderate scenario by month 9

- 4 Starter customers at INR 25,000/month.
- 3 Professional customers at INR 60,000/month.
- 1 Enterprise customer at INR 1.5 lakh/month.
- Monthly recurring revenue: INR 4.3 lakh.
- Annualized run rate: INR 51.6 lakh.

### Strong niche scenario by month 12

- 5 Starter customers at INR 30,000/month.
- 5 Professional customers at INR 75,000/month.
- 2 Enterprise customers at INR 2 lakh/month.
- Monthly recurring revenue: INR 9.25 lakh.
- Annualized run rate: INR 1.11 crore.

These are directional scenarios, not guarantees, but they show why a niche reference-data product can become meaningful even with a small customer base.

## 12. Decision point for moving to Snowflake/Databricks

Do **not** migrate early. Move only when one or more of these happen:

- 3 to 5 paying customers ask for native warehouse delivery.
- Manual monthly delivery becomes operationally messy.
- Buyers require direct data sharing into Snowflake or Databricks.
- Revenue can comfortably absorb platform overhead.[web:85][web:86]

## 13. 12-week action plan

### Weeks 1–2
- Finalize schema, docs, and sample release.
- Build landing page and repo structure.
- Stand up R2/Pages/Dolt workflow.[web:214][web:224][web:217]

### Weeks 3–4
- Build normalization and lineage rules.
- Publish first sample dataset and methodology note.
- Start direct outreach.

### Weeks 5–6
- Run first complete monthly release.
- Add pricing page and subscriber workflow.
- Sign first design partner if possible.

### Weeks 7–8
- Improve product based on feedback.
- Add one premium feature or richer adjustment view.
- Publish 2 more technical posts and one notebook demo.

### Weeks 9–10
- Expand outreach list.
- Refine commercial packaging.
- Add customer onboarding checklist.

### Weeks 11–12
- Review traction.
- Decide whether to continue lean, add paid feeds, or prepare warehouse marketplace migration.

## 14. Biggest risks and mitigations

| Risk | Mitigation |
|---|---|
| Product seen as “just another dataset” | Lead with broken-backtest and symbol-lineage pain points |
| Too much manual work | Keep first releases monthly, not daily |
| Weak buyer trust | Publish methodology, provenance, confidence flags, and changelogs |
| Slow sales | Use direct outreach instead of waiting for inbound |
| Scope creep | Stay NSE-only and reference-data-only in MVP |

## 15. Recommended first move

The best first move is to create a **public sample + paid full release model** on Cloudflare Pages/R2 with Dolt-backed versioning and a strong methodology page. That combination gives you the lowest cost, the fastest proof-of-value, and a clean migration path later to Snowflake or Databricks if customers ask for native delivery.[web:214][web:224][web:217]
