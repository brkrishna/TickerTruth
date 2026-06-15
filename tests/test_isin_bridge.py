"""
Tests for pipelines/lineage/isin_bridge.py

All tests use inline DataFrames — no I/O or network calls.
"""

import pandas as pd
import pytest

from pipelines.lineage.isin_bridge import ISINBridgeBuilder


# ── fixtures ──────────────────────────────────────────────────────────────────


def _nse_securities(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "nse_symbol": "TEST",
        "isin": "INE001A01010",
        "listing_date": "2000-01-01",
        "active_flag": True,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _bse_scrips(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "scrip_code": "500001",
        "isin": "INE001A01010",
        "listing_date": "2000-01-01",
        "active_flag": True,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _nse_actions(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "nse_symbol": "TEST",
        "action_code": "DIVIDEND",
        "event_date": "2026-06-01",
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _bse_actions(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "SCRIP_CODE": "500001",
        "action_code": "DIVIDEND",
        "event_date": "2026-06-01",
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


@pytest.fixture
def builder():
    return ISINBridgeBuilder()


# ── bridge construction tests ─────────────────────────────────────────────────


class TestBuildBridge:
    def test_dual_listed_isin_appears_once(self, builder):
        nse = _nse_securities([{"isin": "INE001A01010", "nse_symbol": "RELIANCE"}])
        bse = _bse_scrips([{"isin": "INE001A01010", "scrip_code": "500325"}])
        bridge = builder.build(nse, bse)
        assert len(bridge) == 1
        row = bridge.iloc[0]
        assert row["nse_symbol"] == "RELIANCE"
        assert row["bse_scrip_code"] == "500325"
        assert not row["is_bse_only"]
        assert not row["is_nse_only"]

    def test_bse_only_isin_flagged(self, builder):
        nse = _nse_securities([{"isin": "INE001A01010"}])
        bse = _bse_scrips(
            [
                {"isin": "INE001A01010"},
                {"isin": "INE999A01010", "scrip_code": "999999"},  # BSE-only
            ]
        )
        bridge = builder.build(nse, bse)
        bse_only = bridge[bridge["is_bse_only"]]
        assert len(bse_only) == 1
        assert bse_only.iloc[0]["isin"] == "INE999A01010"

    def test_nse_only_isin_flagged(self, builder):
        nse = _nse_securities(
            [
                {"isin": "INE001A01010"},
                {"isin": "INE888A01010", "nse_symbol": "NSEONLY"},  # NSE-only
            ]
        )
        bse = _bse_scrips([{"isin": "INE001A01010"}])
        bridge = builder.build(nse, bse)
        nse_only = bridge[bridge["is_nse_only"]]
        assert len(nse_only) == 1
        assert nse_only.iloc[0]["isin"] == "INE888A01010"

    def test_ca_date_conflict_false_by_default(self, builder):
        nse = _nse_securities([{"isin": "INE001A01010"}])
        bse = _bse_scrips([{"isin": "INE001A01010"}])
        bridge = builder.build(nse, bse)
        assert not bridge["ca_date_conflict"].any()

    def test_map_id_is_sequential(self, builder):
        nse = _nse_securities([{"isin": "INE001A01010"}, {"isin": "INE002A01010"}])
        bse = _bse_scrips([{"isin": "INE001A01010"}, {"isin": "INE002A01010"}])
        bridge = builder.build(nse, bse)
        assert list(bridge["map_id"]) == list(range(1, len(bridge) + 1))

    def test_isin_uppercased_on_join(self, builder):
        nse = _nse_securities([{"isin": "ine001a01010"}])
        bse = _bse_scrips([{"isin": "INE001A01010"}])
        bridge = builder.build(nse, bse)
        # Both should match after uppercase normalisation
        assert len(bridge) == 1
        assert not bridge.iloc[0]["is_bse_only"]
        assert not bridge.iloc[0]["is_nse_only"]

    def test_raises_on_missing_isin_column_nse(self, builder):
        nse = pd.DataFrame([{"nse_symbol": "TEST"}])
        bse = _bse_scrips([{"isin": "INE001A01010"}])
        with pytest.raises(ValueError, match="isin"):
            builder.build(nse, bse)

    def test_empty_nse_produces_bse_only_rows(self, builder):
        nse = pd.DataFrame(columns=["nse_symbol", "isin", "listing_date"])
        bse = _bse_scrips([{"isin": "INE001A01010"}])
        bridge = builder.build(nse, bse)
        assert len(bridge) == 1
        assert bridge.iloc[0]["is_bse_only"]


# ── CA date conflict detection tests ─────────────────────────────────────────


class TestFindCADateConflicts:
    def _make_bridge(self, builder):
        nse = _nse_securities([{"isin": "INE001A01010", "nse_symbol": "RELIANCE"}])
        bse = _bse_scrips([{"isin": "INE001A01010", "scrip_code": "500325"}])
        return builder.build(nse, bse)

    def test_no_conflict_when_dates_match(self, builder):
        bridge = self._make_bridge(builder)
        nse = _nse_actions(
            [
                {
                    "nse_symbol": "RELIANCE",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-01",
                }
            ]
        )
        bse = _bse_actions(
            [
                {
                    "SCRIP_CODE": "500325",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-01",
                }
            ]
        )
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge)
        assert len(conflicts) == 0

    def test_conflict_detected_when_dates_differ_beyond_tolerance(self, builder):
        bridge = self._make_bridge(builder)
        nse = _nse_actions(
            [
                {
                    "nse_symbol": "RELIANCE",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-01",
                }
            ]
        )
        bse = _bse_actions(
            [
                {
                    "SCRIP_CODE": "500325",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-10",
                }
            ]
        )
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge, tolerance_days=3)
        assert len(conflicts) == 1
        assert conflicts.iloc[0]["date_diff_days"] == 9

    def test_conflict_within_tolerance_not_flagged(self, builder):
        bridge = self._make_bridge(builder)
        nse = _nse_actions(
            [
                {
                    "nse_symbol": "RELIANCE",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-01",
                }
            ]
        )
        bse = _bse_actions(
            [
                {
                    "SCRIP_CODE": "500325",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-02",
                }
            ]
        )
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge, tolerance_days=3)
        assert len(conflicts) == 0

    def test_severity_high_for_large_diff(self, builder):
        bridge = self._make_bridge(builder)
        nse = _nse_actions(
            [
                {
                    "nse_symbol": "RELIANCE",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-01-01",
                }
            ]
        )
        bse = _bse_actions(
            [
                {
                    "SCRIP_CODE": "500325",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-04-01",
                }
            ]
        )
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge)
        assert conflicts.iloc[0]["conflict_severity"] == "HIGH"

    def test_severity_medium_for_moderate_diff(self, builder):
        bridge = self._make_bridge(builder)
        nse = _nse_actions(
            [
                {
                    "nse_symbol": "RELIANCE",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-01",
                }
            ]
        )
        bse = _bse_actions(
            [
                {
                    "SCRIP_CODE": "500325",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-06-15",
                }
            ]
        )
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge)
        assert conflicts.iloc[0]["conflict_severity"] == "MEDIUM"

    def test_different_action_types_not_compared(self, builder):
        bridge = self._make_bridge(builder)
        nse = _nse_actions(
            [
                {
                    "nse_symbol": "RELIANCE",
                    "action_code": "BONUS",
                    "event_date": "2026-06-01",
                }
            ]
        )
        bse = _bse_actions(
            [
                {
                    "SCRIP_CODE": "500325",
                    "action_code": "DIVIDEND",
                    "event_date": "2026-01-01",
                }
            ]
        )
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge)
        assert len(conflicts) == 0

    def test_empty_actions_returns_empty_conflicts(self, builder):
        bridge = self._make_bridge(builder)
        nse = pd.DataFrame(columns=["nse_symbol", "action_code", "event_date"])
        bse = pd.DataFrame(columns=["SCRIP_CODE", "action_code", "event_date"])
        conflicts = builder.find_ca_date_conflicts(nse, bse, bridge)
        assert len(conflicts) == 0


# ── summarize tests ───────────────────────────────────────────────────────────


class TestSummarize:
    def test_summary_counts_correct(self, builder):
        nse = _nse_securities(
            [
                {"isin": "INE001A01010"},  # dual-listed
                {"isin": "INE002A01010"},  # NSE-only
            ]
        )
        bse = _bse_scrips(
            [
                {"isin": "INE001A01010"},  # dual-listed
                {"isin": "INE003A01010", "scrip_code": "500003"},  # BSE-only
            ]
        )
        bridge = builder.build(nse, bse)
        summary = builder.summarize(bridge)
        assert summary["dual_listed"] == 1
        assert summary["nse_only"] == 1
        assert summary["bse_only"] == 1
        assert summary["total_isins"] == 3
