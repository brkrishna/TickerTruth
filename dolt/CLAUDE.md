# Dolt schema and versioning module

## Purpose
Manages the versioned tabular schema for the India Symbol History and
Corporate Actions Truth Layer product, including DDL, migrations,
seed data, and release tagging.

Dolt is used as the versioned truth store for the product because
corporate-action corrections, late events, and symbol-lineage revisions
need a full audit trail and point-in-time queryability.

## Scope
- Schema DDL for all product tables.
- Migration scripts for schema evolution.
- Seed data for taxonomy lookups and test fixtures.
- Release tagging and changelog management.

## Folder structure
dolt/
├── .dolt/                       ← Dolt internal state (do not edit manually)
├── schema.sql                   ← current full DDL snapshot (auto-generated, do not edit)
├── drop_tables.sql              ← utility script to drop all tables (use with care)
└── seed_corporate_actions.sql   ← seed data for corporate action lookup tables

Note: Migration subdirectories (migration/, seed/, tags/) are planned but not yet created.
New schema changes should be applied as numbered migration files added to a migration/ subfolder
when that pattern is adopted.


## Migration rules
- All schema changes must be written as numbered migration files in `migration/`.
- Migration file names must follow: `NNN_short_snake_case_description.sql`
  where NNN is zero-padded to three digits (001, 002, etc).
- Migrations must be idempotent: safe to run more than once without error.
  Use `IF NOT EXISTS`, `IF EXISTS`, and `CREATE OR REPLACE` where supported.
- Never drop a column in a migration. Instead:
  - Add a `deprecated_at DATE` companion column to the deprecated column.
  - Set `deprecated_at` to the migration date.
  - Remove the column only after two full release cycles have passed.
- Never rename a column directly. Instead:
  - Add the new column.
  - Backfill from the old column.
  - Deprecate the old column.
- Breaking changes require a major version tag and a subscriber notification entry
  in `tags/release-log.md`.
- Every migration must include a comment block at the top:

```sql
-- Migration: NNN_<description>
-- Author: <initials>
-- Date: YYYY-MM-DD
-- Purpose: <one sentence>
-- Breaking: yes/no
-- Rollback: <brief rollback approach or 'not reversible'>
```

## Schema rules
- All table names must be snake_case and plural (e.g., `fact_corporate_action_events`).
- All column names must be snake_case.
- Every table must have:
  - A surrogate primary key (e.g., `id BIGINT AUTO_INCREMENT PRIMARY KEY`
    or equivalent for Dolt).
  - `created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`.
  - `updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`.
- Foreign keys must be declared as column comments if not enforced natively:
  `-- FK: references dim_security_master(security_id)`.
- Add indexes on all columns used in frequent joins or filters:
  `security_id`, `effective_date`, `exchange_symbol`, `isin`.

## Seed data rules
- Seed files live in `seed/` and are safe to re-run (fully idempotent).
- Use `INSERT IGNORE` or `INSERT ... ON DUPLICATE KEY UPDATE` patterns.
- Seed files cover only lookup/taxonomy tables, never transactional facts.
- Seed data must be reviewed and updated when the controlled taxonomy changes.

## Versioning and release tagging rules
- Tag every monthly product release in Dolt using:
  `dolt tag release-YYYY-MM -m "Monthly release YYYY-MM"`
- Record every release tag in `tags/release-log.md` with:
  - Release tag name.
  - Release date.
  - Summary of changes (coverage, corrections, breaking changes).
  - Whether a full chain recalculation was run.
- Point-in-time queries for subscribers must use release tags, not raw commit hashes.
- Never force-push or rebase Dolt commits after a release tag is published.

## Testing rules
- Migration SQL must be validated against a local Dolt instance before committing.
- Seed files must be re-run after each migration to verify idempotency.
- Schema snapshot in `schema.sql` must be regenerated after every migration:
  `dolt schema export > dolt/schema.sql`
- Do not manually edit `schema.sql`; it is always auto-generated.

## Done criteria
- All migrations are idempotent and pass on a clean Dolt instance.
- `schema.sql` reflects the current state of all applied migrations.
- Every release is tagged and logged in `tags/release-log.md`.
- No columns dropped without a two-release deprecation cycle.