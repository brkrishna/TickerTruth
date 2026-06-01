# Lineage module

## Purpose
Detects and records symbol rename history, listing status changes, issuer continuity,
and alias resolution by comparing NSE symbol snapshots across time periods and
cross-referencing with corporate action events.

## Scope
This folder handles:
- Symbol rename, merger, demerger, delisting, suspension, and relisting events.
- Confidence scoring for each detected lineage event.
- Cross-referencing lineage events with corporate actions to boost confidence.
- QA flagging for ambiguous or unresolvable lineage changes.

## Files
- `rules.py` — `LineageEvent` value object and `LineageRulesEngine` (pure detection logic).
- `linker.py` — `SymbolLinker` class: compares snapshot DataFrames across periods,
  calls `LineageRulesEngine`, then cross-references with corporate actions.
- `rules.yaml` — threshold and weight configuration for confidence scoring.

## Event types (controlled taxonomy)
`RENAME` | `MERGER` | `DEMERGER` | `DELISTING` | `RELISTING` | `LISTING` |
`SUSPENSION` | `REACTIVATION`

## Output schema (required columns for every emitted event row)
- `event_type` — from controlled taxonomy above.
- `event_date` — date the event became effective (datetime.date).
- `symbol_from` — prior symbol; None for new listings.
- `symbol_to` — new symbol; None for delistings.
- `confidence` — float 0.0 (guess) to 1.0 (certain).
- `reason` — human-readable explanation string.
- `corroborating_evidence` — list of supporting data point strings.

## Rules
- Preserve reproducibility: outputs must be deterministic for a given input snapshot.
- Never merge issuers based only on fuzzy name matching without a confidence gate.
- Prefer explicit lineage events (sourced from NSE) over inferred symbol continuity.
- If confidence is ambiguous, emit a QA flag rather than guessing.
- Cross-reference with corporate actions within a 30-day window to boost confidence (+0.15).
- Never mutate input DataFrames.

## Testing rules
- Tests live in `tests/test_lineage_*.py`.
- Required test cases:
  - Symbol rename: detected with confidence ≥ 0.8.
  - Temporary suspension and relisting.
  - Mergers and demergers where symbol continuity breaks.
  - Fuzzy name match below threshold: no event emitted, QA flag set.
  - Corporate action corroboration within window: confidence boosted.
  - Determinism: same inputs → identical event list across multiple calls.

## Done criteria
- `pytest tests/test_lineage_*.py -q` passes with no warnings.
- `ruff check pipelines/lineage/` passes.
- No input DataFrames mutated.
- Every emitted event has all required output schema columns populated.
