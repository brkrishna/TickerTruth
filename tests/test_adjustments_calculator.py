"""
Tests for pipelines/adjustments/calculator.py (AdjustmentCalculator).

Covers the required test cases from pipelines/adjustments/CLAUDE.md that
apply to what's actually implemented here (pure split/bonus/reverse-split
math — the module doesn't yet implement RIGHTS, FACE_VALUE_CHANGE,
MERGER/DEMERGER factors, confidence_flag, or duplicate-event handling; see
tests/test_adjustments_adjuster.py's module docstring for that gap):
- Split: standard 2:1 and 10:1 cases (parametrized).
- Bonus: 1:1, 1:2, 3:1 (parametrized).
- Zero denominator: ValueError raised.
- Determinism: same input -> same output across repeated calls.

All tests are pure — no I/O, no network calls.
"""

import pandas as pd
import pytest

from pipelines.adjustments.calculator import AdjustmentCalculator


# ── calculate_split_adjustment ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "old_numerator,new_denominator,expected",
    [
        (1, 2, 0.5),  # standard 1:2 split
        (1, 10, 0.1),  # 1:10 split
        (2, 1, 2.0),  # 2:1 reverse split — factor > 1
    ],
)
def test_calculate_split_adjustment(old_numerator, new_denominator, expected):
    factor = AdjustmentCalculator.calculate_split_adjustment(
        old_numerator, new_denominator
    )
    assert factor == pytest.approx(expected)


@pytest.mark.parametrize(
    "old_numerator,new_denominator", [(0, 2), (1, 0), (-1, 2), (1, -2)]
)
def test_calculate_split_adjustment_rejects_non_positive(
    old_numerator, new_denominator
):
    with pytest.raises(ValueError, match="must be positive"):
        AdjustmentCalculator.calculate_split_adjustment(old_numerator, new_denominator)


# ── calculate_bonus_adjustment ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "existing_shares,bonus_shares,expected",
    [
        (1, 1, 0.5),  # 1:1 bonus
        (1, 2, 1 / 3),  # 1:2 bonus (2 bonus shares per 1 existing)
        (3, 1, 0.75),  # 3:1 bonus (1 bonus share per 3 existing)
    ],
)
def test_calculate_bonus_adjustment(existing_shares, bonus_shares, expected):
    factor = AdjustmentCalculator.calculate_bonus_adjustment(
        existing_shares, bonus_shares
    )
    assert factor == pytest.approx(expected)


@pytest.mark.parametrize(
    "existing_shares,bonus_shares", [(0, 1), (1, 0), (-1, 1), (1, -1)]
)
def test_calculate_bonus_adjustment_rejects_non_positive(existing_shares, bonus_shares):
    with pytest.raises(ValueError, match="must be positive"):
        AdjustmentCalculator.calculate_bonus_adjustment(existing_shares, bonus_shares)


# ── calculate_cumulative_adjustment ──────────────────────────────────────────


def test_calculate_cumulative_adjustment_single_split():
    events = pd.DataFrame([{"action_code": "SPLIT", "old_value": 0.5}])
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result["cumulative_split_adjustment"] == pytest.approx(0.5)
    assert result["cumulative_bonus_adjustment"] == pytest.approx(1.0)
    assert result["total_adjustment_factor"] == pytest.approx(0.5)


def test_calculate_cumulative_adjustment_split_then_bonus_compounds():
    events = pd.DataFrame(
        [
            {"action_code": "SPLIT", "old_value": 0.5},
            {"action_code": "BONUS", "old_value": 0.5},
        ]
    )
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result["cumulative_split_adjustment"] == pytest.approx(0.5)
    assert result["cumulative_bonus_adjustment"] == pytest.approx(0.5)
    assert result["total_adjustment_factor"] == pytest.approx(0.25)


def test_calculate_cumulative_adjustment_multiple_splits_compound():
    events = pd.DataFrame(
        [
            {"action_code": "SPLIT", "old_value": 0.5},
            {"action_code": "SPLIT", "old_value": 0.5},
        ]
    )
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result["cumulative_split_adjustment"] == pytest.approx(0.25)


def test_calculate_cumulative_adjustment_reverse_split_multiplies_split_factor():
    events = pd.DataFrame([{"action_code": "REVERSE_SPLIT", "old_value": 2.0}])
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result["cumulative_split_adjustment"] == pytest.approx(2.0)
    assert result["total_adjustment_factor"] == pytest.approx(2.0)


def test_calculate_cumulative_adjustment_ignores_unknown_action_code():
    events = pd.DataFrame(
        [
            {"action_code": "DIVIDEND", "old_value": 5.0},
            {"action_code": "SPLIT", "old_value": 0.5},
        ]
    )
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result["cumulative_split_adjustment"] == pytest.approx(0.5)
    assert result["total_adjustment_factor"] == pytest.approx(0.5)


def test_calculate_cumulative_adjustment_skips_null_value_rows():
    events = pd.DataFrame(
        [
            {"action_code": "SPLIT", "old_value": None},
            {"action_code": "SPLIT", "old_value": 0.5},
        ]
    )
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result["cumulative_split_adjustment"] == pytest.approx(0.5)


def test_calculate_cumulative_adjustment_empty_events_returns_identity():
    events = pd.DataFrame(columns=["action_code", "old_value"])
    result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert result == {
        "cumulative_split_adjustment": 1.0,
        "cumulative_bonus_adjustment": 1.0,
        "total_adjustment_factor": 1.0,
    }


@pytest.mark.parametrize("code", ["SPLIT", "BONUS", "REVERSE_SPLIT"])
def test_calculate_cumulative_adjustment_zero_value_raises(code):
    events = pd.DataFrame([{"action_code": code, "old_value": 0.0}])
    with pytest.raises(ValueError, match="Invalid"):
        AdjustmentCalculator.calculate_cumulative_adjustment(events)


@pytest.mark.parametrize("code", ["SPLIT", "BONUS", "REVERSE_SPLIT"])
def test_calculate_cumulative_adjustment_negative_value_raises(code):
    events = pd.DataFrame([{"action_code": code, "old_value": -0.5}])
    with pytest.raises(ValueError, match="Invalid"):
        AdjustmentCalculator.calculate_cumulative_adjustment(events)


# ── determinism ───────────────────────────────────────────────────────────────


def test_calculate_cumulative_adjustment_deterministic():
    events = pd.DataFrame(
        [
            {"action_code": "SPLIT", "old_value": 0.5},
            {"action_code": "BONUS", "old_value": 0.5},
        ]
    )
    first = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    second = AdjustmentCalculator.calculate_cumulative_adjustment(events)
    assert first == second


def test_calculate_cumulative_adjustment_does_not_mutate_input():
    events = pd.DataFrame([{"action_code": "SPLIT", "old_value": 0.5}])
    events_before = events.copy()
    AdjustmentCalculator.calculate_cumulative_adjustment(events)
    pd.testing.assert_frame_equal(events, events_before)
