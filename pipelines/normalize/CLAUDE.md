# Normalize module

## Purpose
Standardizes raw NSE source data into clean, typed, canonically named
DataFrames ready for downstream lineage and adjustment processing.
This module does not write to any database or file system directly.

## Scope
- Field renaming to snake_case
- Date and timestamp parsing
- Numeric type enforcement
- Null and missing value handling
- Payer / exchange / action-type canonical mapping
- Symbol name cleaning and whitespace normalization

## Pure function rules
- Every transform function must be pure: same input always produces same output.
- No file I/O, no database calls, no API calls inside any function in this module.
- No global state or mutable default arguments.
- Functions must accept DataFrames or Series as inputs and return new DataFrames
  or Series. Never mutate the input.
- Side effects such as logging are acceptable but must not affect return values.

## Column naming rules
- All output column names must be snake_case.
- No spaces, hyphens, camelCase, or PascalCase in column names.
- Boolean columns must be prefixed with `is_` or `has_`.
- Date columns must be suffixed with `_date`.
- Timestamp columns must be suffixed with `_at`.
- Amount or ratio columns must include unit hints where ambiguous
  (e.g., `amount_inr`, `ratio_numerator`, `price_adjusted`).

## Date and timestamp rules
- All date fields must be parsed to `datetime.date`, never left as string or object dtype.
- All timestamp fields must be parsed to `datetime.datetime` with timezone awareness
  where the source provides timezone info.
- If a date field is missing or unparseable, set to `None` and emit a
  `parse_warning` flag column for that row.
- Never use `pd.to_datetime` without explicit `errors='coerce'` and
  a follow-up null check.
- Do not infer date formats automatically; always pass explicit `format=` argument.

## Numeric type rules
- All price fields must be `float64`.
- All volume and count fields must be `Int64` (nullable integer).
- All ratio fields (split ratio, bonus ratio) must be stored as
  separate `ratio_numerator` and `ratio_denominator` columns, both `Int64`.
- Never store ratios as pre-divided floats in the staging layer.
- Unknown or unparseable numeric values must become `None`, not zero or -1.

## Null handling rules
- Never drop rows silently. If a row cannot be normalized, add a
  `normalization_error` column with a short reason string and retain the row.
- Required fields that are null after normalization must be flagged with
  a `_missing` boolean companion column (e.g., `effective_date_missing`).
- Optional fields that are null are acceptable without flagging.

## Canonical mapping rules
- Maintain canonical lookup tables in `pipelines/normalize/field_mappings.yaml`.
- Exchange codes must map to: NSE / BSE / NSE_SME / BSE_SME.
- Action type strings from raw sources must map to the controlled taxonomy:
  SPLIT / BONUS / DIVIDEND_CASH / RIGHTS / MERGER / DEMERGER /
  SYMBOL_CHANGE / NAME_CHANGE / FACE_VALUE_CHANGE / DELISTING /
  SUSPENSION / RELISTING.
- Unrecognized action types must map to UNKNOWN and emit a warning log.
- Payer/issuer names must be whitespace-stripped, title-cased,
  and suffix-normalized (Ltd → Limited, Pvt → Private).

## Testing rules
- Tests live in `tests/test_normalize_<module>.py`.
- Every public function must have at least:
  - One happy-path test with valid input.
  - One edge-case test (empty DataFrame, single row, all-null column).
  - One invalid-input test (wrong dtype, missing required column).
- Tests must not read from disk or make network calls.
- Use small inline DataFrames as fixtures, not external CSV files.

## Done criteria
- `ruff check pipelines/normalize/` passes with no errors.
- `pytest tests/test_normalize_*.py -q` passes with no warnings.
- No input DataFrames are mutated.
- No file or network I/O inside any function.