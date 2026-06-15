"""
Tests for pipelines/lineage/bse_scrip_history.py

Uses inline DataFrames — no file I/O or network calls.
All detection logic must be deterministic (same inputs → same output).
"""

from datetime import date

import pandas as pd
import pytest

from pipelines.lineage.bse_scrip_history import BSEScripHistoryBuilder


# ── fixtures ──────────────────────────────────────────────────────────────────


def _make_scrip_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal dim_bse_scrip_master DataFrame from a list of dicts."""
    defaults = {
        "scrip_code": "500001",
        "scrip_name": "TEST",
        "isin": "INE001A01010",
        "active_flag": True,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


EVENT_DATE = date(2026, 6, 1)


@pytest.fixture
def builder():
    return BSEScripHistoryBuilder()


# ── listing detection ─────────────────────────────────────────────────────────


class TestListingDetection:
    def test_new_scrip_detected_as_listing(self, builder):
        previous = _make_scrip_df([{"scrip_code": "500001", "scrip_name": "OLD"}])
        current = _make_scrip_df(
            [
                {"scrip_code": "500001", "scrip_name": "OLD"},
                {"scrip_code": "500002", "scrip_name": "NEW", "isin": "INE002A01010"},
            ]
        )
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        listings = events[events["event_type"] == "LISTING"]
        assert len(listings) == 1
        assert listings.iloc[0]["scrip_code"] == "500002"

    def test_listing_confidence_is_high(self, builder):
        previous = _make_scrip_df([{"scrip_code": "500001"}])
        current = _make_scrip_df(
            [
                {"scrip_code": "500001"},
                {"scrip_code": "500002", "isin": "INE002A01010"},
            ]
        )
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        listing = events[events["event_type"] == "LISTING"].iloc[0]
        assert listing["confidence"] >= 0.9

    def test_no_events_when_snapshots_identical(self, builder):
        scrips = _make_scrip_df([{"scrip_code": "500001"}, {"scrip_code": "500002"}])
        events = builder.build_lineage_events(scrips, scrips.copy(), EVENT_DATE)
        assert len(events) == 0


# ── delisting detection ───────────────────────────────────────────────────────


class TestDelistingDetection:
    def test_removed_scrip_detected_as_delisting(self, builder):
        previous = _make_scrip_df(
            [
                {"scrip_code": "500001"},
                {"scrip_code": "500002", "scrip_name": "GONE", "isin": "INE002A01010"},
            ]
        )
        current = _make_scrip_df([{"scrip_code": "500001"}])
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        delistings = events[events["event_type"] == "DELISTING"]
        assert len(delistings) == 1
        assert delistings.iloc[0]["scrip_code"] == "500002"

    def test_delisting_records_old_scrip_name(self, builder):
        previous = _make_scrip_df(
            [
                {"scrip_code": "500001"},
                {"scrip_code": "500099", "scrip_name": "OLDCO", "isin": "INE099A01010"},
            ]
        )
        current = _make_scrip_df([{"scrip_code": "500001"}])
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        delisting = events[events["event_type"] == "DELISTING"].iloc[0]
        assert delisting["scrip_name_old"] == "OLDCO"


# ── rename detection ──────────────────────────────────────────────────────────


class TestRenameDetection:
    def test_name_change_detected_when_isin_same(self, builder):
        isin = "INE001A01010"
        previous = _make_scrip_df(
            [{"scrip_code": "500001", "scrip_name": "OLD_CO", "isin": isin}]
        )
        current = _make_scrip_df(
            [{"scrip_code": "500001", "scrip_name": "NEW_CO", "isin": isin}]
        )
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        renames = events[events["event_type"] == "RENAME"]
        assert len(renames) == 1
        assert renames.iloc[0]["scrip_name_old"] == "OLD_CO"
        assert renames.iloc[0]["scrip_name_new"] == "NEW_CO"

    def test_rename_confidence_higher_with_matching_isin(self, builder):
        isin = "INE001A01010"
        previous = _make_scrip_df(
            [{"scrip_code": "500001", "scrip_name": "ALPHA", "isin": isin}]
        )
        current = _make_scrip_df(
            [{"scrip_code": "500001", "scrip_name": "BETA", "isin": isin}]
        )
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        rename = events[events["event_type"] == "RENAME"].iloc[0]
        assert rename["confidence"] >= 0.8

    def test_no_rename_when_name_unchanged(self, builder):
        row = {"scrip_code": "500001", "scrip_name": "SAME", "isin": "INE001A01010"}
        events = builder.build_lineage_events(
            _make_scrip_df([row]), _make_scrip_df([row]), EVENT_DATE
        )
        renames = events[events["event_type"] == "RENAME"]
        assert len(renames) == 0


# ── code reassignment detection ───────────────────────────────────────────────


class TestCodeReassignmentDetection:
    def test_different_isin_on_same_code_detected_as_code_reassign(self, builder):
        previous = _make_scrip_df(
            [{"scrip_code": "500001", "isin": "INE001A01010", "scrip_name": "OLD"}]
        )
        current = _make_scrip_df(
            [{"scrip_code": "500001", "isin": "INE999A01010", "scrip_name": "NEW"}]
        )
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        reassigns = events[events["event_type"] == "CODE_REASSIGN"]
        assert len(reassigns) == 1
        assert reassigns.iloc[0]["scrip_code"] == "500001"

    def test_code_reassign_confidence_below_rename(self, builder):
        previous = _make_scrip_df([{"scrip_code": "500001", "isin": "INE001A01010"}])
        current = _make_scrip_df([{"scrip_code": "500001", "isin": "INE002A01010"}])
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        reassign = events[events["event_type"] == "CODE_REASSIGN"].iloc[0]
        assert reassign["confidence"] < 0.9  # less certain than a clean rename


# ── status change detection ───────────────────────────────────────────────────


class TestStatusChangeDetection:
    def test_active_to_inactive_detected(self, builder):
        previous = _make_scrip_df([{"scrip_code": "500001", "active_flag": True}])
        current = _make_scrip_df([{"scrip_code": "500001", "active_flag": False}])
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        status_events = events[
            events["event_type"].isin(["STATUS_CHANGE", "DELISTING"])
        ]
        assert len(status_events) >= 1

    def test_relisting_detected_when_active_flag_restored(self, builder):
        previous = _make_scrip_df([{"scrip_code": "500001", "active_flag": False}])
        current = _make_scrip_df([{"scrip_code": "500001", "active_flag": True}])
        events = builder.build_lineage_events(previous, current, EVENT_DATE)
        relistings = events[events["event_type"] == "RELISTING"]
        assert len(relistings) == 1


# ── determinism ───────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_inputs_produce_identical_output(self, builder):
        previous = _make_scrip_df([{"scrip_code": "500001", "scrip_name": "A"}])
        current = _make_scrip_df(
            [
                {"scrip_code": "500001", "scrip_name": "B"},
                {"scrip_code": "500002", "scrip_name": "C", "isin": "INE002A01010"},
            ]
        )
        events1 = builder.build_lineage_events(previous, current, EVENT_DATE)
        events2 = builder.build_lineage_events(previous, current, EVENT_DATE)
        pd.testing.assert_frame_equal(
            events1.reset_index(drop=True),
            events2.reset_index(drop=True),
        )


# ── status history builder ────────────────────────────────────────────────────


class TestBuildStatusHistory:
    def test_active_scrip_gets_active_status(self, builder):
        scrips = _make_scrip_df([{"scrip_code": "500001", "active_flag": True}])
        hist = builder.build_status_history(scrips, as_of_date=EVENT_DATE)
        assert hist.iloc[0]["status"] == "ACTIVE"

    def test_inactive_scrip_gets_delisted_status(self, builder):
        scrips = _make_scrip_df([{"scrip_code": "500001", "active_flag": False}])
        hist = builder.build_status_history(scrips, as_of_date=EVENT_DATE)
        assert hist.iloc[0]["status"] == "DELISTED"

    def test_effective_date_matches_input(self, builder):
        scrips = _make_scrip_df([{"scrip_code": "500001"}])
        hist = builder.build_status_history(scrips, as_of_date=EVENT_DATE)
        assert hist.iloc[0]["effective_date"] == "2026-06-01"

    def test_returns_one_row_per_scrip(self, builder):
        scrips = _make_scrip_df(
            [
                {"scrip_code": "500001"},
                {"scrip_code": "500002"},
                {"scrip_code": "500003"},
            ]
        )
        hist = builder.build_status_history(scrips, as_of_date=EVENT_DATE)
        assert len(hist) == 3
