"""
Tests for pipelines/normalize/bse_normalizer.py

All tests use inline DataFrames — no file I/O, no network calls.
"""

import pandas as pd
import pytest

from pipelines.normalize.bse_normalizer import (
    BSERawToCanonicalMapper,
    normalize_bse_action_type,
)


# ── fixtures ──────────────────────────────────────────────────────────────────


def _make_raw_scrips(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "SCRIP_CODE": str(500000 + i).zfill(6),
                "SCRIP_NAME": f"SCRIP{i}",
                "COMPANY_NAME": f"Company {i} Ltd",
                "ISIN": f"INE{i:09d}",
                "STATUS": "Active",
                "SEGMENT": "Equity",
                "LISTING_DATE": "01-01-2000",
            }
            for i in range(n)
        ]
    )


def _make_raw_actions(scrip_codes: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "SCRIP_CODE": code,
                "ACTION_TYPE_RAW": "Dividend",
                "EX_DATE": "01/06/2026",
                "RECORD_DATE": "02/06/2026",
                "PAYMENT_DATE": "10/06/2026",
            }
            for code in scrip_codes
        ]
    )


@pytest.fixture
def mapper():
    return BSERawToCanonicalMapper(source_file="bse_scrips_consolidated.csv")


@pytest.fixture
def raw_scrips():
    return _make_raw_scrips(5)


@pytest.fixture
def dim_bse(mapper, raw_scrips):
    return mapper.map_to_dim_bse_scrip_master(raw_scrips)


# ── action type normalisation tests ──────────────────────────────────────────


class TestNormalizeBSEActionType:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Dividend", "DIVIDEND"),
            ("interim dividend", "DIVIDEND"),
            ("Final Dividend", "DIVIDEND"),
            ("Bonus Issue", "BONUS"),
            ("bonus", "BONUS"),
            ("Stock Split", "SPLIT"),
            ("Sub-Division", "SPLIT"),
            ("Sub Division", "SPLIT"),
            ("Face Value Split", "SPLIT"),
            ("Stock Consolidation", "REVERSE_SPLIT"),
            ("Consolidation", "REVERSE_SPLIT"),
            ("Rights Issue", "RIGHTS"),
            ("Merger", "MERGER"),
            ("Amalgamation", "MERGER"),
            ("Demerger", "DEMERGER"),
            ("Name Change", "NAME_CHANGE"),
            ("Delisting", "DELISTING"),
            ("Voluntary Delisting", "DELISTING"),
            ("Face Value Change", "FACE_VALUE_CHANGE"),
            ("Capital Reduction", "CAPITAL_REDUCTION"),
            ("Interim Dividend - Rs.2.00 per share", "DIVIDEND"),  # decorated string
        ],
    )
    def test_known_bse_action_types(self, raw, expected):
        assert normalize_bse_action_type(raw) == expected

    def test_unknown_returns_unknown(self):
        assert normalize_bse_action_type("Some Exotic Corporate Event") == "UNKNOWN"

    def test_none_returns_unknown(self):
        assert normalize_bse_action_type(None) == "UNKNOWN"

    def test_empty_returns_unknown(self):
        assert normalize_bse_action_type("") == "UNKNOWN"

    def test_case_insensitive(self):
        assert normalize_bse_action_type("BONUS ISSUE") == "BONUS"
        assert normalize_bse_action_type("bonus issue") == "BONUS"
        assert normalize_bse_action_type("Bonus Issue") == "BONUS"


# ── dim_bse_scrip_master mapping tests ───────────────────────────────────────


class TestMapToDimBSEScripMaster:
    def test_output_has_required_columns(self, mapper, raw_scrips):
        df = mapper.map_to_dim_bse_scrip_master(raw_scrips)
        required = ["scrip_id", "scrip_code", "isin", "scrip_name", "active_flag"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_scrip_code_zero_padded(self, mapper):
        scrips = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "500325",
                    "SCRIP_NAME": "RELI",
                    "ISIN": "INE002A01018",
                    "STATUS": "Active",
                }
            ]
        )
        df = mapper.map_to_dim_bse_scrip_master(scrips)
        assert df["scrip_code"].iloc[0] == "500325"

    def test_active_flag_true_for_active(self, mapper, raw_scrips):
        df = mapper.map_to_dim_bse_scrip_master(raw_scrips)
        assert df["active_flag"].all()

    def test_active_flag_false_for_delisted(self, mapper):
        scrips = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "500001",
                    "SCRIP_NAME": "X",
                    "ISIN": "INE001",
                    "STATUS": "Delisted",
                },
                {
                    "SCRIP_CODE": "500002",
                    "SCRIP_NAME": "Y",
                    "ISIN": "INE002",
                    "STATUS": "Active",
                },
            ]
        )
        df = mapper.map_to_dim_bse_scrip_master(scrips)
        assert not df.loc[df["scrip_code"] == "500001", "active_flag"].iloc[0]
        assert df.loc[df["scrip_code"] == "500002", "active_flag"].iloc[0]

    def test_isin_uppercased_and_stripped(self, mapper):
        scrips = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "500001",
                    "SCRIP_NAME": "X",
                    "ISIN": "  ine002a01018  ",
                    "STATUS": "Active",
                }
            ]
        )
        df = mapper.map_to_dim_bse_scrip_master(scrips)
        assert df["isin"].iloc[0] == "INE002A01018"

    def test_listing_date_parsed(self, mapper):
        scrips = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "500001",
                    "SCRIP_NAME": "X",
                    "ISIN": "INE001",
                    "LISTING_DATE": "28-05-2000",
                }
            ]
        )
        df = mapper.map_to_dim_bse_scrip_master(scrips)
        assert df["listing_date"].iloc[0] == "2000-05-28"

    def test_dedup_on_scrip_code_keeps_last(self, mapper):
        scrips = pd.DataFrame(
            [
                {"SCRIP_CODE": "500001", "SCRIP_NAME": "OLD_NAME", "STATUS": "Active"},
                {"SCRIP_CODE": "500001", "SCRIP_NAME": "NEW_NAME", "STATUS": "Active"},
            ]
        )
        df = mapper.map_to_dim_bse_scrip_master(scrips)
        assert len(df) == 1
        assert df["scrip_name"].iloc[0] == "NEW_NAME"

    def test_raises_on_missing_scrip_code_column(self, mapper):
        scrips = pd.DataFrame([{"ISIN": "INE001", "SCRIP_NAME": "X"}])
        with pytest.raises(ValueError, match="SCRIP_CODE"):
            mapper.map_to_dim_bse_scrip_master(scrips)

    def test_quality_columns_added(self, mapper, raw_scrips):
        df = mapper.map_to_dim_bse_scrip_master(raw_scrips)
        assert "_confidence_score" in df.columns
        assert "_quality_issues" in df.columns
        assert "_manual_review_required" in df.columns

    def test_company_name_normalized(self, mapper):
        scrips = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "500001",
                    "SCRIP_NAME": "REL",
                    "COMPANY_NAME": "Reliance  Industries  Ltd.",
                    "STATUS": "Active",
                }
            ]
        )
        df = mapper.map_to_dim_bse_scrip_master(scrips)
        assert "LIMITED" in df["company_name"].iloc[0]

    def test_empty_dataframe_returns_empty(self, mapper):
        df = mapper.map_to_dim_bse_scrip_master(
            pd.DataFrame(columns=["SCRIP_CODE", "SCRIP_NAME", "ISIN"])
        )
        assert len(df) == 0


# ── fact_bse_corporate_action_event tests ────────────────────────────────────


class TestMapToFactBSECorporateActionEvent:
    def test_output_has_required_columns(self, mapper, dim_bse):
        codes = dim_bse["scrip_code"].tolist()[:3]
        raw_actions = _make_raw_actions(codes)
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        required = [
            "scrip_id",
            "action_code",
            "event_date",
            "confidence_score",
            "confidence_flag",
            "exchange_id",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_exchange_id_is_bse(self, mapper, dim_bse):
        codes = dim_bse["scrip_code"].tolist()[:2]
        raw_actions = _make_raw_actions(codes)
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        assert (df["exchange_id"] == 2).all()

    def test_action_code_normalised(self, mapper, dim_bse):
        codes = dim_bse["scrip_code"].tolist()[:1]
        raw_actions = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": codes[0],
                    "ACTION_TYPE_RAW": "Bonus Issue",
                    "EX_DATE": "01/06/2026",
                }
            ]
        )
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        assert df["action_code"].iloc[0] == "BONUS"

    def test_missing_ex_date_lowers_confidence(self, mapper, dim_bse):
        codes = dim_bse["scrip_code"].tolist()[:1]
        raw_actions = pd.DataFrame(
            [{"SCRIP_CODE": codes[0], "ACTION_TYPE_RAW": "Dividend", "EX_DATE": None}]
        )
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        # Should have penalty for missing ex_date
        assert df["confidence_score"].iloc[0] < 0.9
        assert "BSE_MISSING_EX_DATE" in df["_quality_issues"].iloc[0]

    def test_unresolved_scrip_code_flagged(self, mapper, dim_bse):
        raw_actions = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "999999",
                    "ACTION_TYPE_RAW": "Dividend",
                    "EX_DATE": "01/06/2026",
                }
            ]
        )
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        assert df["scrip_id"].isna().all()
        assert df["confidence_score"].iloc[0] <= 0.7

    def test_confidence_flag_high_for_clean_row(self, mapper, dim_bse):
        codes = dim_bse["scrip_code"].tolist()[:1]
        raw_actions = _make_raw_actions(codes)
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        assert df["confidence_flag"].iloc[0] in ("HIGH", "MEDIUM")

    def test_raises_on_missing_required_columns(self, mapper, dim_bse):
        bad_df = pd.DataFrame([{"ISIN": "INE001"}])
        with pytest.raises(ValueError, match="SCRIP_CODE"):
            mapper.map_to_fact_bse_corporate_action_event(bad_df, dim_bse)

    def test_date_parsed_from_dd_mm_yyyy(self, mapper, dim_bse):
        codes = dim_bse["scrip_code"].tolist()[:1]
        raw_actions = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": codes[0],
                    "ACTION_TYPE_RAW": "Dividend",
                    "EX_DATE": "01/06/2026",
                }
            ]
        )
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        assert df["event_date"].iloc[0] == "2026-06-01"

    def test_empty_actions_returns_empty(self, mapper, dim_bse):
        raw_actions = pd.DataFrame(columns=["SCRIP_CODE", "ACTION_TYPE_RAW", "EX_DATE"])
        df = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
        assert len(df) == 0
