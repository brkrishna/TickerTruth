# TickerTruth — India Symbol History and Corporate Actions Truth Layer

A low-cost, versioned reference-data product for NSE-listed equities symbol lineage and corporate actions.

## Purpose
This project is a zero-to-low-cost MVP designed to validate demand for a trustworthy symbol history and corporate-action reference layer for India's financial markets. Built with a Python-led ETL stack, Dolt versioning, and Cloudflare delivery, the product ships as monthly versioned bundles rather than a real-time API.

The goal is to:

- Solve the broken-backtest problem caused by incorrect ticker history and missing corporate action adjustments
- Sell early subscriptions manually to validate buyer willingness to pay
- Keep infrastructure costs minimal until customers pull toward warehouse-native delivery
- Maintain the simplest possible delivery model while building credibility

## Key documents
- [Design](design.md) — technical architecture, data model, boundary conditions, and migration paths
- [Tasks](tasks.md) — phase-by-phase implementation checklist and progress tracking

## Quick start

 - See [design.md](design.md) for technical design and constraints
 - See [tasks.md](tasks.md) for implementation phases and checkpoints