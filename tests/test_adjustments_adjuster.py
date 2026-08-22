"""
Tests for pipelines/adjustments/adjuster.py (AdjustmentFactorBuilder).

Covers the required test cases from pipelines/adjustments/CLAUDE.md that
apply to what's actually implemented here. Note: the current implementation
is narrower than the module's aspirational spec — it only handles
SPLIT/BONUS/REVERSE_SPLIT (not RIGHTS, FACE_VALUE_CHANGE, MERGER, DEMERGER),
has no confidence_flag column, and on a zero/negative old_value it silently
skips the offending event with a logged warning rather than deduplicating
per a `duplicate_group_id` or emitting an UNRESOLVED flag. Tests below
document actual behavior; CLAUDE.md's test cases that require unimplemented
features (Rights, Face value change, Missing effective_date -> UNRESOLVED
flag, Duplicate events -> UNRESOLVED flag, dividend factor passthrough) are
not applicable yet and are not faked here.

Covered:
- Split: standard case via the full builder pipeline.
- Bonus: standard case via the full builder pipeline.
- Multiple securities: independent cumulative chains.
- Out-of-order event arrival: cumulative chain is correct after sort.
- Non-adjustable action codes (e.g. DIVIDEND) are filtered out.
- Zero/negative old_value: event skipped (not a hard failure) — logged as
  a warning, chain continues from the last valid state.
- Missing required columns: ValueError raised.
- Duplicate (security_id, as_of_date): _validate_factors raises ValueError.
- Never mutate input DataFrames.

All tests are pure — no I/O, no network calls.
"""

import pandas as pd
import pytest

from pipelines.adjustments.adjuster import AdjustmentFactorBuilder


@pytest.fixture()
def builder():
    return AdjustmentFactorBuilder()


def _actions(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ── build_from_corporate_actions: happy paths ───────────────────────────────


def test_build_from_corporate_actions_single_split(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-15",
                "old_value": 0.5,
            }
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert len(out) == 1
    row = out.iloc[0]
    assert row["security_id"] == 1
    assert row["as_of_date"] == "2026-01-15"
    assert row["cumulative_split_adjustment"] == pytest.approx(0.5)
    assert row["cumulative_bonus_adjustment"] == pytest.approx(1.0)
    assert row["total_adjustment_factor"] == pytest.approx(0.5)
    assert row["cumulative_dividend_adjustment"] == 1.0


def test_build_from_corporate_actions_single_bonus(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "BONUS",
                "event_date": "2026-01-15",
                "old_value": 0.5,
            }
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert out.iloc[0]["cumulative_bonus_adjustment"] == pytest.approx(0.5)
    assert out.iloc[0]["total_adjustment_factor"] == pytest.approx(0.5)


def test_build_from_corporate_actions_cumulative_chain_compounds(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01",
                "old_value": 0.5,
            },
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-06-01",
                "old_value": 0.5,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert len(out) == 2
    first, second = out.iloc[0], out.iloc[1]
    assert first["cumulative_split_adjustment"] == pytest.approx(0.5)
    assert second["cumulative_split_adjustment"] == pytest.approx(0.25)


def test_build_from_corporate_actions_multiple_securities_independent_chains(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01",
                "old_value": 0.5,
            },
            {
                "security_id": 2,
                "action_code": "BONUS",
                "event_date": "2026-01-01",
                "old_value": 0.5,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    sec1 = out[out["security_id"] == 1].iloc[0]
    sec2 = out[out["security_id"] == 2].iloc[0]
    assert sec1["cumulative_split_adjustment"] == pytest.approx(0.5)
    assert sec1["cumulative_bonus_adjustment"] == pytest.approx(1.0)
    assert sec2["cumulative_split_adjustment"] == pytest.approx(1.0)
    assert sec2["cumulative_bonus_adjustment"] == pytest.approx(0.5)


def test_build_from_corporate_actions_out_of_order_events_sorted_before_chaining(
    builder,
):
    # Deliberately out of chronological order in the input.
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-06-01",
                "old_value": 0.5,
            },
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01",
                "old_value": 0.25,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    out_sorted = out.sort_values("as_of_date").reset_index(drop=True)
    # 2026-01-01 (factor 0.25) applied first, then 2026-06-01 (factor 0.5)
    assert out_sorted.iloc[0]["as_of_date"] == "2026-01-01"
    assert out_sorted.iloc[0]["cumulative_split_adjustment"] == pytest.approx(0.25)
    assert out_sorted.iloc[1]["as_of_date"] == "2026-06-01"
    assert out_sorted.iloc[1]["cumulative_split_adjustment"] == pytest.approx(0.125)


def test_build_from_corporate_actions_filters_non_adjustable_codes(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "DIVIDEND",
                "event_date": "2026-01-01",
                "old_value": 5.0,
            },
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-02-01",
                "old_value": 0.5,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert len(out) == 1
    assert out.iloc[0]["as_of_date"] == "2026-02-01"


def test_build_from_corporate_actions_only_non_adjustable_returns_empty(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "DIVIDEND",
                "event_date": "2026-01-01",
                "old_value": 5.0,
            }
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert out.empty
    for col in [
        "security_id",
        "as_of_date",
        "cumulative_split_adjustment",
        "cumulative_bonus_adjustment",
        "cumulative_dividend_adjustment",
        "total_adjustment_factor",
    ]:
        assert col in out.columns


# ── edge cases ───────────────────────────────────────────────────────────────


def test_build_from_corporate_actions_missing_required_columns_raises(builder):
    actions = pd.DataFrame([{"security_id": 1}])  # missing action_code, event_date
    with pytest.raises(ValueError, match="missing required columns"):
        builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())


def test_build_from_corporate_actions_skips_zero_value_event(builder):
    """
    A zero old_value on a SPLIT row makes AdjustmentCalculator raise
    ValueError; the builder catches that per-event and skips the row
    (logged as a warning) rather than failing the whole build — the chain
    continues from its last valid state for subsequent events.
    """
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01",
                "old_value": 0.0,
            },
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-02-01",
                "old_value": 0.5,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    # Only the valid second event produces an output row.
    assert len(out) == 1
    assert out.iloc[0]["as_of_date"] == "2026-02-01"
    assert out.iloc[0]["cumulative_split_adjustment"] == pytest.approx(0.5)


def test_build_from_corporate_actions_unparseable_event_date_dropped(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "not-a-date",
                "old_value": 0.5,
            },
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-02-01",
                "old_value": 0.5,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert len(out) == 1
    assert out.iloc[0]["as_of_date"] == "2026-02-01"


def test_build_from_corporate_actions_empty_input_returns_typed_empty_df(builder):
    actions = pd.DataFrame(
        columns=["security_id", "action_code", "event_date", "old_value"]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert out.empty
    assert "security_id" in out.columns


def test_build_from_corporate_actions_does_not_mutate_input(builder):
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01",
                "old_value": 0.5,
            }
        ]
    )
    actions_before = actions.copy()
    builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())
    pd.testing.assert_frame_equal(actions, actions_before)


def test_build_from_corporate_actions_duplicate_as_of_date_raises_via_validation(
    builder,
):
    """
    Two SPLIT events for the same security on the same date produce two
    output rows with an identical (security_id, as_of_date) key, which
    _validate_factors() rejects.
    """
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01T09:00:00",
                "old_value": 0.5,
            },
            {
                "security_id": 1,
                "action_code": "SPLIT",
                "event_date": "2026-01-01T15:00:00",
                "old_value": 0.5,
            },
        ]
    )
    with pytest.raises(ValueError, match="duplicate"):
        builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())


def test_build_from_corporate_actions_merges_events_on_identical_event_date(builder):
    """
    Two distinct events for the same security sharing the exact same
    event_date (not just the same calendar day — the literal same parsed
    timestamp, as happens when NSE reports two corporate actions on one
    ex-date) must be merged into a single output row rather than producing
    a duplicate (security_id, as_of_date) key.
    """
    actions = _actions(
        [
            {
                "security_id": 1,
                "action_code": "BONUS",
                "event_date": "2026-08-21",
                "old_value": 0.75,
            },
            {
                "security_id": 1,
                "action_code": "BONUS",
                "event_date": "2026-08-21",
                "old_value": 0.5,
            },
        ]
    )
    out = builder.build_from_corporate_actions(actions, symbols=pd.DataFrame())

    assert len(out) == 1
    assert out.iloc[0]["as_of_date"] == "2026-08-21"
    assert out.iloc[0]["cumulative_bonus_adjustment"] == pytest.approx(0.75 * 0.5)


# ── _validate_factors (direct) ───────────────────────────────────────────────


def test_validate_factors_raises_on_non_positive_factor():
    bad = pd.DataFrame(
        [
            {
                "security_id": 1,
                "as_of_date": "2026-01-01",
                "cumulative_split_adjustment": 0.0,
                "cumulative_bonus_adjustment": 1.0,
                "total_adjustment_factor": 0.0,
            }
        ]
    )
    with pytest.raises(ValueError, match="non-positive"):
        AdjustmentFactorBuilder._validate_factors(bad)


def test_validate_factors_raises_on_total_mismatch():
    bad = pd.DataFrame(
        [
            {
                "security_id": 1,
                "as_of_date": "2026-01-01",
                "cumulative_split_adjustment": 0.5,
                "cumulative_bonus_adjustment": 0.5,
                "total_adjustment_factor": 0.9,  # should be 0.25
            }
        ]
    )
    with pytest.raises(ValueError, match="split . bonus"):
        AdjustmentFactorBuilder._validate_factors(bad)


def test_validate_factors_passes_on_consistent_rows():
    good = pd.DataFrame(
        [
            {
                "security_id": 1,
                "as_of_date": "2026-01-01",
                "cumulative_split_adjustment": 0.5,
                "cumulative_bonus_adjustment": 0.5,
                "total_adjustment_factor": 0.25,
            },
            {
                "security_id": 2,
                "as_of_date": "2026-01-01",
                "cumulative_split_adjustment": 1.0,
                "cumulative_bonus_adjustment": 1.0,
                "total_adjustment_factor": 1.0,
            },
        ]
    )
    AdjustmentFactorBuilder._validate_factors(good)  # should not raise
