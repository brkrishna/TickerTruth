# Adjustments module

## Purpose
Computes event-level and cumulative price/quantity adjustment factors
for NSE corporate actions. Produces an audit-ready factor chain that
downstream consumers can use to restate historical price series.

## Scope
- Adjustment factor computation for: SPLIT, BONUS, RIGHTS, FACE_VALUE_CHANGE,
  MERGER, DEMERGER.
- Cash dividends (DIVIDEND_CASH) do not produce a price-adjustment factor
  in this module; they are noted but passed through with factor = 1.0.
- Cumulative factor chain maintenance across the full security history.
- Confidence flagging for uncertain or conflicting events.

## Factor chain rules
- Adjustment direction is backward only: historical prices are restated,
  current prices are never forward-adjusted.
- Sort all events by effective_date ascending before computing cumulative chain.
- Cumulative factor = product of all prior event-level factors for that security,
  ordered by effective_date.
- A factor of exactly 1.0 means no price adjustment at that event.
- Never allow a factor of zero or negative; guard against division by zero
  in ratio calculations and raise a ValueError with the offending row.
- If two events share the same effective_date for the same security,
  apply them in action_type precedence order:
  FACE_VALUE_CHANGE → SPLIT → BONUS → RIGHTS → MERGER → DEMERGER.
- Recalculate the full cumulative chain when any historical event is
  corrected or inserted late.

## Output schema (required columns for every output row)
- `security_id` — durable internal identifier, not ticker.
- `effective_date` — date of the corporate action event.
- `action_id` — FK to fact_corporate_action_event.
- `action_type` — from controlled taxonomy.
- `factor` — event-level adjustment factor (float64).
- `cumulative_factor` — running product of all factors up to and including
  this event (float64).
- `confidence_flag` — HIGH / MEDIUM / LOW / UNRESOLVED.
- `created_at` — processing timestamp (datetime with timezone).

## Confidence flag rules
- HIGH: event sourced from official exchange feed with complete ratio data.
- MEDIUM: event sourced from scraped page or inferred from price series.
- LOW: event ratio is estimated or source is ambiguous.
- UNRESOLVED: conflicting data from two or more sources; do not use in
  production analytics without manual review.

## Edge case handling rules
- Missing effective_date: emit the row with effective_date = None,
  factor = 1.0, confidence_flag = UNRESOLVED, and log a warning.
  Do not drop the row.
- Duplicate events (same security_id + effective_date + action_type):
  deduplicate by taking the highest-confidence source; if equal confidence,
  flag as UNRESOLVED and retain both rows with a `duplicate_group_id`.
- Out-of-order event arrival: always re-sort and recompute the full
  cumulative chain rather than appending incrementally.
- Zero ratio_denominator: raise ValueError immediately with event details.
- Ratio where numerator equals denominator (1:1 bonus): valid; factor = 0.5.
- Rights issue: factor accounts for both price dilution and quantity change;
  use the theoretical ex-rights price formula.

## Pure function rules
- All computation functions must be pure: same input → same output.
- No database calls, file I/O, or API calls inside compute functions.
- Orchestration (reading inputs, writing outputs) belongs in separate
  pipeline runner scripts, not inside this module.
- Never mutate input DataFrames.

## Testing rules
- Tests live in `tests/test_adjustments_factors.py`.
- Use `pytest.mark.parametrize` for ratio variants (1:2, 2:1, 3:1, 1:1 etc).
- Use fixtures for shared security master and action event DataFrames.
- Required test cases:
  - Split: standard 2:1 and 10:1 cases.
  - Bonus: 1:1, 1:2, 3:1.
  - Cash dividend: verify factor = 1.0.
  - Rights: price and quantity dilution.
  - Face value change: no price adjustment, chain continuity.
  - Missing effective_date: UNRESOLVED flag emitted.
  - Out-of-order events: cumulative chain is correct after sort.
  - Duplicate events: deduplication logic and UNRESOLVED flag.
  - Zero denominator: ValueError raised.
  - Full chain recalculation after a late historical correction.

## Done criteria
- `pytest tests/test_adjustments_factors.py -q` passes with no warnings.
- `ruff check pipelines/adjustments/` passes.
- No input DataFrames mutated.
- No zero or negative factors emitted without a ValueError.
- Every output row has all required output schema columns populated
  (nullable columns may be None but must exist).