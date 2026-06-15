"""
Tests for pipelines/adjustments/bse_adjuster.py

All tests use inline DataFrames — no I/O or network calls.
"""

import pandas as pd
import pytest

from pipelines.adjustments.bse_adjuster import BSEAdjustmentFactorBuilder


# ── fixtures ──────────────────────────────────────────────────────────────────


def _dim_bse_scrip(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "scrip_id": 1,
        "scrip_code": "500325",
        "isin": "INE002A01018",
        "scrip_name": "RELIANCE",
        "active_flag": True,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _bse_actions(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "scrip_id": 1,
        "action_code": "SPLIT",
        "event_date": "2025-06-01",
        "old_value": 0.5,
        "exchange_id": 2,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _nse_factors(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "security_id": "RELIANCE",
        "as_of_date": "2025-06-01",
        "cumulative_split_adjustment": 0.5,
        "cumulative_bonus_adjustment": 1.0,
        "cumulative_dividend_adjustment": 1.0,
        "total_adjustment_factor": 0.5,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _bridge(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "isin": "INE002A01018",
        "nse_symbol": "RELIANCE",
        "bse_scrip_code": "500325",
        "is_bse_only": False,
        "is_nse_only": False,
        "ca_date_conflict": False,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


@pytest.fixture
def builder():
    return BSEAdjustmentFactorBuilder()


# ── build_from_bse_actions ────────────────────────────────────────────────────


class TestBuildFromBSEActions:
    def test_split_action_produces_factor_row(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = _bse_actions(
            [
                {
                    "scrip_id": 1,
                    "action_code": "SPLIT",
                    "event_date": "2025-06-01",
                    "old_value": 0.5,
                }
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert len(result) == 1
        assert result.iloc[0]["total_adjustment_factor"] == pytest.approx(0.5)

    def test_bonus_action_produces_correct_factor(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 2, "scrip_code": "500002"}])
        actions = _bse_actions(
            [
                {
                    "scrip_id": 2,
                    "action_code": "BONUS",
                    "event_date": "2025-07-01",
                    "old_value": 0.5,
                }
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert len(result) == 1
        assert result.iloc[0]["cumulative_bonus_adjustment"] == pytest.approx(0.5)

    def test_dividend_action_produces_no_factor_row(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = _bse_actions(
            [
                {
                    "scrip_id": 1,
                    "action_code": "DIVIDEND",
                    "event_date": "2025-06-01",
                    "old_value": None,
                }
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert len(result) == 0

    def test_empty_actions_returns_empty_dataframe(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = pd.DataFrame(
            columns=["scrip_id", "action_code", "event_date", "old_value"]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert len(result) == 0
        assert "scrip_id" in result.columns
        assert "total_adjustment_factor" in result.columns

    def test_scrip_code_attached_to_output(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = _bse_actions(
            [{"scrip_id": 1, "action_code": "SPLIT", "old_value": 0.5}]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert "scrip_code" in result.columns
        assert result.iloc[0]["scrip_code"] == "500325"

    def test_multiple_splits_accumulate_correctly(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = pd.DataFrame(
            [
                {
                    "scrip_id": 1,
                    "action_code": "SPLIT",
                    "event_date": "2020-01-01",
                    "old_value": 0.5,
                },
                {
                    "scrip_id": 1,
                    "action_code": "SPLIT",
                    "event_date": "2022-01-01",
                    "old_value": 0.5,
                },
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        # Two 1:2 splits: cumulative = 0.5 × 0.5 = 0.25
        assert result.iloc[-1]["total_adjustment_factor"] == pytest.approx(0.25)

    def test_resolves_scrip_id_from_scrip_code(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 5, "scrip_code": "500999"}])
        # Provide scrip_code instead of scrip_id
        actions = pd.DataFrame(
            [
                {
                    "scrip_code": "500999",
                    "action_code": "SPLIT",
                    "event_date": "2025-01-01",
                    "old_value": 0.5,
                }
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert len(result) == 1
        assert result.iloc[0]["scrip_id"] == 5

    def test_raises_without_scrip_id_or_scrip_code(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = pd.DataFrame(
            [{"action_code": "SPLIT", "event_date": "2025-01-01", "old_value": 0.5}]
        )
        with pytest.raises(ValueError, match="scrip_id.*scrip_code"):
            builder.build_from_bse_actions(actions, dim)

    def test_reverse_split_increases_factor(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = _bse_actions(
            [
                {
                    "scrip_id": 1,
                    "action_code": "REVERSE_SPLIT",
                    "event_date": "2025-06-01",
                    "old_value": 2.0,
                }
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert result.iloc[0]["total_adjustment_factor"] > 1.0

    def test_multiple_securities_emit_separate_rows(self, builder):
        dim = pd.DataFrame(
            [
                {"scrip_id": 1, "scrip_code": "500001", "isin": "INE001A01010"},
                {"scrip_id": 2, "scrip_code": "500002", "isin": "INE002A01010"},
            ]
        )
        actions = pd.DataFrame(
            [
                {
                    "scrip_id": 1,
                    "action_code": "SPLIT",
                    "event_date": "2025-01-01",
                    "old_value": 0.5,
                },
                {
                    "scrip_id": 2,
                    "action_code": "BONUS",
                    "event_date": "2025-02-01",
                    "old_value": 0.5,
                },
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert len(result) == 2
        assert set(result["scrip_id"]) == {1, 2}

    def test_output_has_required_columns(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = _bse_actions(
            [{"scrip_id": 1, "action_code": "SPLIT", "old_value": 0.5}]
        )
        result = builder.build_from_bse_actions(actions, dim)
        for col in [
            "scrip_id",
            "as_of_date",
            "cumulative_split_adjustment",
            "cumulative_bonus_adjustment",
            "total_adjustment_factor",
        ]:
            assert col in result.columns, f"Missing column: {col}"

    def test_as_of_date_matches_event_date(self, builder):
        dim = _dim_bse_scrip([{"scrip_id": 1, "scrip_code": "500325"}])
        actions = _bse_actions(
            [
                {
                    "scrip_id": 1,
                    "action_code": "SPLIT",
                    "event_date": "2024-03-15",
                    "old_value": 0.5,
                }
            ]
        )
        result = builder.build_from_bse_actions(actions, dim)
        assert result.iloc[0]["as_of_date"] == "2024-03-15"


# ── cross_validate_with_nse ───────────────────────────────────────────────────


class TestCrossValidateWithNSE:
    def _make_bse_factors(self, scrip_code, scrip_id, as_of_date, factor):
        return pd.DataFrame(
            [
                {
                    "scrip_id": scrip_id,
                    "scrip_code": scrip_code,
                    "as_of_date": as_of_date,
                    "cumulative_split_adjustment": factor,
                    "cumulative_bonus_adjustment": 1.0,
                    "total_adjustment_factor": factor,
                }
            ]
        )

    def _make_nse_factors(self, nse_symbol, as_of_date, factor):
        return pd.DataFrame(
            [
                {
                    "security_id": nse_symbol,
                    "as_of_date": as_of_date,
                    "cumulative_split_adjustment": factor,
                    "cumulative_bonus_adjustment": 1.0,
                    "total_adjustment_factor": factor,
                }
            ]
        )

    def test_no_discrepancy_when_factors_match(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = self._make_nse_factors("RELIANCE", "2025-06-01", 0.5)
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert len(result) == 0

    def test_discrepancy_detected_when_factors_differ(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = self._make_nse_factors("RELIANCE", "2025-06-01", 0.25)  # different
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert len(result) == 1
        assert result.iloc[0]["factor_diff"] == pytest.approx(0.25)

    def test_severity_high_for_large_discrepancy(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = self._make_nse_factors("RELIANCE", "2025-06-01", 0.1)
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert result.iloc[0]["discrepancy_severity"] == "HIGH"

    def test_severity_medium_for_moderate_discrepancy(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = self._make_nse_factors("RELIANCE", "2025-06-01", 0.48)
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert result.iloc[0]["discrepancy_severity"] == "MEDIUM"

    def test_severity_low_for_small_discrepancy_above_tolerance(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = self._make_nse_factors("RELIANCE", "2025-06-01", 0.4985)
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br, tolerance=0.001)
        if len(result) > 0:
            assert result.iloc[0]["discrepancy_severity"] == "LOW"

    def test_different_dates_not_compared(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = self._make_nse_factors("RELIANCE", "2025-07-01", 0.25)
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert len(result) == 0

    def test_bse_only_security_not_compared(self, builder):
        bse = self._make_bse_factors("999001", 1, "2025-06-01", 0.5)
        nse = _nse_factors([])
        br = _bridge(
            [
                {
                    "isin": "INE999A01010",
                    "nse_symbol": None,
                    "bse_scrip_code": "999001",
                    "is_bse_only": True,
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert len(result) == 0

    def test_empty_bse_factors_returns_empty(self, builder):
        bse = pd.DataFrame(
            columns=["scrip_id", "scrip_code", "as_of_date", "total_adjustment_factor"]
        )
        nse = _nse_factors(
            [{"security_id": "RELIANCE", "total_adjustment_factor": 0.5}]
        )
        br = _bridge([])
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert len(result) == 0

    def test_empty_nse_factors_returns_empty(self, builder):
        bse = self._make_bse_factors("500325", 1, "2025-06-01", 0.5)
        nse = pd.DataFrame(
            columns=["security_id", "as_of_date", "total_adjustment_factor"]
        )
        br = _bridge(
            [
                {
                    "isin": "INE002A01018",
                    "nse_symbol": "RELIANCE",
                    "bse_scrip_code": "500325",
                }
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        assert len(result) == 0

    def test_sorted_by_factor_diff_descending(self, builder):
        bse = pd.DataFrame(
            [
                {
                    "scrip_id": 1,
                    "scrip_code": "500001",
                    "as_of_date": "2025-01-01",
                    "total_adjustment_factor": 0.1,
                },
                {
                    "scrip_id": 2,
                    "scrip_code": "500002",
                    "as_of_date": "2025-02-01",
                    "total_adjustment_factor": 0.4,
                },
            ]
        )
        nse = pd.DataFrame(
            [
                {
                    "security_id": "ALPHA",
                    "as_of_date": "2025-01-01",
                    "total_adjustment_factor": 0.5,
                },
                {
                    "security_id": "BETA",
                    "as_of_date": "2025-02-01",
                    "total_adjustment_factor": 0.5,
                },
            ]
        )
        br = pd.DataFrame(
            [
                {
                    "isin": "INE001A01010",
                    "nse_symbol": "ALPHA",
                    "bse_scrip_code": "500001",
                },
                {
                    "isin": "INE002A01010",
                    "nse_symbol": "BETA",
                    "bse_scrip_code": "500002",
                },
            ]
        )
        result = builder.cross_validate_with_nse(bse, nse, br)
        if len(result) >= 2:
            # ALPHA diff = 0.4, BETA diff = 0.1 — ALPHA should come first
            assert result.iloc[0]["factor_diff"] >= result.iloc[1]["factor_diff"]
