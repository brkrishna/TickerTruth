# India Symbol Truth Layer — Implementation Tasks

## Purpose

This document tracks progress across phases, checkpoints, and deliverables for the MVP build.

## Phase 1 — Setup and foundation

1. Project scaffolding
   - create repo structure
   - add `README.md`, `.gitignore`, and docs placeholders
   - define Python dependency management and environment
        - create .venv with python3 -m venv .venv
        - add requirements.txt or pyproject.toml
        - add pip install instructions for the venv   
2. Schema design
   - define table schemas for dimensions and facts
   - create Dolt schema files, seed data, and migrations
3. Source inventory
   - document NSE and corporate action sources
   - specify extraction targets and expected formats
4. Website/docs scaffold
   - establish Cloudflare Pages site structure
   - add product overview, methodology, pricing, and sample query docs

## Phase 2 — Data ingestion and normalization

5. Raw extraction pipeline
   - implement raw data fetch from NSE and action sources
   - persist raw files to `data/raw/`
   - consolidate data into staging files
6. Normalization pipeline
   - build data cleaning and canonicalization
   - map raw fields into the core schema
   - add provenance and quality metadata
7. Lineage pipeline
   - create ticker/name history rules
   - identify renames, splits, mergers, and delistings
   - output `fact_symbol_lineage_event`
8. Adjustment factor pipeline
   - compute corporate action adjustment factors
   - cross-check with symbol history for backtest readiness
   - output `fact_adjustment_factor`

## Phase 3 — Versioning, QA, and publishing

9. Dolt integration
   - initialize Dolt repo and import schema
   - implement Dolt load and commit logic
   - manage versioned repository change history
10. QA and validation
   - implement core data quality checks
   - create unit and integration tests in `tests/`
   - add validation for lineage, duplicates, and date consistency
11. Export and publishing
   - generate public sample CSV/Parquet releases
   - generate paid full release bundles
   - store outputs in `releases/monthly/`
12. Documentation and release notes
   - publish release notes and changelog updates
   - add sample SQL and usage examples

## Phase 4 — Automation and maintenance

13. CI/CD automation
   - add GitHub Actions for lint, tests, and docs site build
   - schedule weekly or nightly data refresh workflows
14. Release workflow automation
   - automate artifact generation on release events
   - automate R2 uploads and manifest updates
   - auto-update changelog metadata where feasible
15. Operational runbook
   - document manual refresh and release procedures
   - add troubleshooting steps for Dolt and workflows
   - define monitoring and failure recovery checks

## Phase 5 — Delivery and customer access

16. Packaging and pricing
   - define Explorer, Starter, Professional bundle contents
   - implement packaging logic for sample and paid bundles
17. Access model
   - define private R2 link delivery and DoltHub access process
   - document manual onboarding and payment steps
18. Future readiness
   - preserve schemas and sample queries for data warehouse migration
   - keep export logic decoupled from delivery channels

## Checkpoints and commits

- `phase-1-complete` — repo scaffold, schema design, docs scaffold
- `phase-2-complete` — extraction, normalization, lineage, adjustment pipelines
- `phase-3-complete` — Dolt integration, QA, export workflow, publish assets
- `phase-4-complete` — CI/CD automation, release automation, runbook
- `phase-5-complete` — delivery packaging, customer access, future migration readiness

## Progress tracking notes

- Track failures and manual effort per release
- Capture scope changes or boundary exceptions
- Note when a task moves from manual to automated
