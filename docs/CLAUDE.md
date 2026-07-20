# Docs module

## Purpose
Contains all subscriber-facing and internal product documentation including
methodology notes, release notes, sample queries, schema references,
pricing pages, and onboarding guides.

## Scope
- `product-overview.md` — what the product is and who it is for.
- `methodology.md` — how corporate actions are sourced, normalized, and resolved.
- `release-notes.md` — monthly changelog for subscribers.
- `pricing.md` — tier descriptions and subscription options.
- `sample-queries.md` — ready-to-run SQL examples for each product view.
- `onboarding.md` — how to get started with trial access.
- `runbook.md` — operational procedures for data refresh and release.
- `dolt_workflow.md` — Dolt commit, tagging, and point-in-time query procedures.
- `source-inventory.md` — catalog of all upstream data sources.
- `publishing.md` — blog authoring/publishing workflow (StackEdit → GitHub PR → Cloudflare Pages) and Substack/Medium/LinkedIn cross-posting.

Note: `schema-reference.md` and `faq.md` are planned but not yet written.

## Tone rules
- Professional and factual. No marketing superlatives.
- Write for a technically literate audience (data engineers, quant analysts,
  fintech product teams). Do not over-explain basics.
- Use active voice and short sentences.
- Avoid internal engineering jargon (e.g., do not mention pipeline names,
  internal system identifiers, raw source URLs, or staging layer details).
- Avoid phrases like "simply", "just", "easy", "straightforward".
- Do not make claims about data completeness that cannot be verified.

## Release notes format rules
Every monthly release note entry in `release-notes.md` must follow this structure:

```md
# Release YYYY-MM — <Short Title>

**Released:** YYYY-MM-DD
**Records Updated:** <count>
**New Symbols:** <count>
**Corrections:** <count>

### Highlights
- <Key change or addition>
- <Major fix or enhancement>

### Data Changes
- **Dimension updates:** <e.g., 5 new issuers, 2 renamed companies>
- **Corporate actions:** <e.g., 12 new dividend records, 3 splits>
- **Adjustments:** <e.g., recalculated split chain for SYMBOL>

### Quality Improvements
- <QA check added or fixed>

### Known Issues
- <Any outstanding data gaps or limitations; or "None.">

### Next Release
- <Planned work for next month>
```