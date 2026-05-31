"""
Phase 2 unit tests and pipeline data validation.

Run all unit tests:
    pytest pipelines/phase2_validator.py -v

Run data validation against real staged files:
    python pipelines/phase2_validator.py

Tests are organized by task and grow as each pipeline component is built.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
DATA_STAGING = PROJECT_ROOT / "data" / "staging"
DATA_CURATED = PROJECT_ROOT / "data" / "curated"

# ═══════════════════════════════════════════════════════════════════════════════
# TASK 5 — Extraction
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask5Extraction:

    def test_extractor_imports(self):
        from pipelines.extract.extractor import RawDataExtractor
        e = RawDataExtractor()
        assert e.output_dir.name == "raw"

    def test_bhavcopy_url_format(self):
        from pipelines.extract.extractor import RawDataExtractor
        e = RawDataExtractor()
        url = e._bhavcopy_url(date(2024, 5, 28))
        assert "2024" in url
        assert "MAY" in url
        assert "28" in url
        assert url.endswith("cm28MAY2024bhav.csv.zip")

    def test_bhavcopy_url_zero_padded_day(self):
        from pipelines.extract.extractor import RawDataExtractor
        e = RawDataExtractor()
        url = e._bhavcopy_url(date(2024, 1, 3))
        assert "cm03JAN2024bhav.csv.zip" in url

    def test_date_chunks_single(self):
        from pipelines.extract.extractor import RawDataExtractor
        chunks = list(RawDataExtractor._date_chunks(date(2024, 1, 1), date(2024, 1, 15), 30))
        assert len(chunks) == 1
        assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 15))

    def test_date_chunks_multiple(self):
        from pipelines.extract.extractor import RawDataExtractor
        chunks = list(RawDataExtractor._date_chunks(date(2024, 1, 1), date(2024, 3, 31), 30))
        assert len(chunks) == 4
        # No gaps: each chunk_to + 1 day = next chunk_from
        for i in range(len(chunks) - 1):
            from datetime import timedelta
            assert chunks[i][1] + timedelta(days=1) == chunks[i + 1][0]

    def test_date_chunks_covers_full_range(self):
        from pipelines.extract.extractor import RawDataExtractor
        from_d, to_d = date(2024, 1, 1), date(2024, 12, 31)
        chunks = list(RawDataExtractor._date_chunks(from_d, to_d, 30))
        assert chunks[0][0]  == from_d
        assert chunks[-1][1] == to_d

    def test_consolidate_staging_empty(self, tmp_path):
        from pipelines.extract.extractor import RawDataExtractor
        e = RawDataExtractor(output_dir=tmp_path / "raw")
        report = e.consolidate_to_staging(staging_dir=tmp_path / "staging")
        assert report["symbols"]["files_found"] == 0
        assert report["bhavcopy"]["files_found"] == 0

    def test_consolidate_staging_deduplicates(self, tmp_path):
        from pipelines.extract.extractor import RawDataExtractor

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        # Write two symbol files with one overlapping row
        for fname in ["nse_symbols_2024-01-01.csv", "nse_symbols_2024-01-02.csv"]:
            pd.DataFrame([
                {"SYMBOL": "INFY", "LISTING_DATE": "1993-06-03", "STATUS": "ACTIVE"},
                {"SYMBOL": "TCS",  "LISTING_DATE": "2004-08-25", "STATUS": "ACTIVE"},
            ]).to_csv(raw_dir / fname, index=False)

        e = RawDataExtractor(output_dir=raw_dir)
        report = e.consolidate_to_staging(staging_dir=tmp_path / "staging")
        assert report["symbols"]["files_found"] == 2
        # 4 rows in, 2 unique — dedup should reduce to 2
        assert report["symbols"]["rows_after_dedup"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 6 — Normalization
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask6FieldNormalizer:

    def setup_method(self):
        from pipelines.normalize.normalizers import FieldNormalizer
        self.fn = FieldNormalizer

    def test_ticker_strips_eq_suffix(self):
        assert self.fn.normalize_ticker("INFY-EQ") == "INFY"

    def test_ticker_strips_repl_suffix(self):
        assert self.fn.normalize_ticker("RELI-REPL") == "RELI"

    def test_ticker_uppercases(self):
        assert self.fn.normalize_ticker("tcs") == "TCS"

    def test_ticker_strips_whitespace(self):
        assert self.fn.normalize_ticker("  INFY  ") == "INFY"

    def test_ticker_none_returns_empty(self):
        assert self.fn.normalize_ticker(None) == ""

    def test_date_dd_mm_yyyy(self):
        assert self.fn.normalize_date("28-05-2024") == date(2024, 5, 28)

    def test_date_yyyy_mm_dd(self):
        assert self.fn.normalize_date("2024-05-28") == date(2024, 5, 28)

    def test_date_dd_mmm_yyyy(self):
        assert self.fn.normalize_date("28-MAY-2024") == date(2024, 5, 28)

    def test_date_none_returns_none(self):
        assert self.fn.normalize_date(None) is None

    def test_date_na_string_returns_none(self):
        assert self.fn.normalize_date("N/A") is None

    def test_action_type_bonus(self):
        assert self.fn.normalize_action_type("Bonus Issue") == "BONUS"

    def test_action_type_split(self):
        assert self.fn.normalize_action_type("Stock Split") == "SPLIT"

    def test_action_type_partial_match(self):
        assert self.fn.normalize_action_type("Interim Dividend - Rs.5") == "DIVIDEND"

    def test_action_type_unknown(self):
        assert self.fn.normalize_action_type("Something Completely New") == "UNKNOWN"

    def test_action_type_none(self):
        assert self.fn.normalize_action_type(None) == "UNKNOWN"

    def test_numeric_currency_strip(self):
        assert self.fn.normalize_numeric("₹5.00") == 5.0

    def test_numeric_indian_comma(self):
        assert self.fn.normalize_numeric("1,00,000") == 100000.0

    def test_numeric_ratio(self):
        assert self.fn.normalize_numeric("1:2") == 0.5

    def test_numeric_percent(self):
        assert abs(self.fn.normalize_numeric("10%") - 0.10) < 1e-9

    def test_numeric_na_returns_none(self):
        assert self.fn.normalize_numeric("N/A") is None

    def test_company_name_ltd(self):
        assert self.fn.normalize_company_name("Infosys Ltd.") == "INFOSYS LIMITED"

    def test_company_name_pvt(self):
        result = self.fn.normalize_company_name("ABC Pvt. Ltd.")
        assert "PRIVATE" in result and "LIMITED" in result

    def test_company_name_strips_whitespace(self):
        assert self.fn.normalize_company_name("  TCS  ") == "TCS"


class TestTask6QualityMetadata:

    def _make_df(self):
        return pd.DataFrame([
            {"SYMBOL": "INFY", "ISIN": "INE009A01021", "LISTING_DATE": "1993-06-03"},
            {"SYMBOL": None,   "ISIN": None,             "LISTING_DATE": None},
        ])

    def test_adds_five_quality_columns(self):
        from pipelines.normalize.quality import QualityMetadata
        qm  = QualityMetadata(source_file="test.csv")
        out = qm.add_quality_flags(self._make_df())
        for col in ["_source_file", "_extracted_date", "_quality_issues",
                    "_confidence_score", "_manual_review_required"]:
            assert col in out.columns, f"Missing column: {col}"

    def test_clean_row_has_full_score(self):
        from pipelines.normalize.quality import QualityMetadata
        qm  = QualityMetadata(source_file="test.csv")
        out = qm.add_quality_flags(self._make_df())
        assert out.loc[0, "_confidence_score"] == 1.0

    def test_null_row_has_reduced_score(self):
        from pipelines.normalize.quality import QualityMetadata
        qm  = QualityMetadata(source_file="test.csv")
        out = qm.add_quality_flags(self._make_df())
        assert out.loc[1, "_confidence_score"] < 1.0

    def test_null_row_requires_review(self):
        from pipelines.normalize.quality import QualityMetadata
        qm  = QualityMetadata(source_file="test.csv")
        out = qm.add_quality_flags(self._make_df())
        assert out.loc[1, "_manual_review_required"] == True

    def test_source_file_propagated(self):
        from pipelines.normalize.quality import QualityMetadata
        qm  = QualityMetadata(source_file="my_file.csv")
        out = qm.add_quality_flags(self._make_df())
        assert (out["_source_file"] == "my_file.csv").all()


class TestTask6Mapper:

    def _raw_symbols(self):
        return pd.DataFrame([
            {"SYMBOL": "INFY-EQ", "COMPANY_NAME": "Infosys Ltd.",
             "ISIN": "INE009A01021", "LISTING_DATE": "03-06-1993",
             "STATUS": "ACTIVE", "SECTOR": "IT"},
            {"SYMBOL": "TCS", "COMPANY_NAME": "Tata Consultancy Services Ltd.",
             "ISIN": "INE467B01029", "LISTING_DATE": "25-08-2004",
             "STATUS": "ACTIVE", "SECTOR": "IT"},
            {"SYMBOL": "DEFUNCT", "COMPANY_NAME": "Old Corp Ltd.",
             "ISIN": "INE000X00000", "LISTING_DATE": "01-01-2000",
             "STATUS": "DELISTED", "SECTOR": "OTHER"},
        ])

    def test_dim_issuer_row_count(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m  = RawToCanonicalMapper()
        df = m.map_to_dim_issuer(self._raw_symbols())
        assert len(df) == 3

    def test_dim_issuer_has_required_cols(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m   = RawToCanonicalMapper()
        df  = m.map_to_dim_issuer(self._raw_symbols())
        for col in ["issuer_id", "issuer_name", "sector", "country"]:
            assert col in df.columns

    def test_dim_issuer_ids_unique(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m  = RawToCanonicalMapper()
        df = m.map_to_dim_issuer(self._raw_symbols())
        assert df["issuer_id"].nunique() == len(df)

    def test_dim_security_ticker_normalised(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m       = RawToCanonicalMapper()
        issuers = m.map_to_dim_issuer(self._raw_symbols())
        sec     = m.map_to_dim_security_master(self._raw_symbols(), issuers)
        assert "INFY" in sec["nse_symbol"].values
        assert "INFY-EQ" not in sec["nse_symbol"].values

    def test_dim_security_active_flag(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m       = RawToCanonicalMapper()
        issuers = m.map_to_dim_issuer(self._raw_symbols())
        sec     = m.map_to_dim_security_master(self._raw_symbols(), issuers)
        delisted = sec[sec["nse_symbol"] == "DEFUNCT"]
        assert len(delisted) == 1
        assert delisted.iloc[0]["active_flag"] == False

    def test_fact_corp_actions_normalises_codes(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m       = RawToCanonicalMapper()
        issuers = m.map_to_dim_issuer(self._raw_symbols())
        sec     = m.map_to_dim_security_master(self._raw_symbols(), issuers)
        actions = pd.DataFrame([
            {"SYMBOL": "INFY", "ACTION_TYPE_RAW": "Bonus Issue",
             "EX_DATE": "12-01-2024", "RECORD_DATE": "13-01-2024",
             "PAYMENT_DATE": None, "VALUE_OR_RATIO": "1:1"},
        ])
        facts = m.map_to_fact_corporate_action_event(actions, sec)
        assert facts.iloc[0]["action_code"] == "BONUS"
        assert facts.iloc[0]["old_value"]   == 1.0

    def test_fact_corp_actions_unresolved_symbol_flagged(self):
        from pipelines.normalize.normalizer import RawToCanonicalMapper
        m       = RawToCanonicalMapper()
        issuers = m.map_to_dim_issuer(self._raw_symbols())
        sec     = m.map_to_dim_security_master(self._raw_symbols(), issuers)
        actions = pd.DataFrame([
            {"SYMBOL": "UNKNOWN_SYM", "ACTION_TYPE_RAW": "Bonus Issue",
             "EX_DATE": "12-01-2024", "RECORD_DATE": None,
             "PAYMENT_DATE": None, "VALUE_OR_RATIO": "1:1"},
        ])
        facts = m.map_to_fact_corporate_action_event(actions, sec)
        # security_id should be NaN (unresolved), confidence should be < 1
        assert pd.isna(facts.iloc[0]["security_id"])
        assert facts.iloc[0]["confidence_score"] < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 7 — Lineage
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask7LineageEvent:

    def test_valid_event_type(self):
        from pipelines.lineage.rules import LineageEvent
        ev = LineageEvent("RENAME", date(2024, 1, 1), 0.9, "OLD", "NEW")
        assert ev.event_type == "RENAME"

    def test_invalid_event_type_raises(self):
        from pipelines.lineage.rules import LineageEvent
        with pytest.raises(ValueError, match="Unknown event_type"):
            LineageEvent("BOGUS", date(2024, 1, 1), 0.9)

    def test_invalid_confidence_raises(self):
        from pipelines.lineage.rules import LineageEvent
        with pytest.raises(ValueError, match="confidence"):
            LineageEvent("RENAME", date(2024, 1, 1), 1.5, "A", "B")

    def test_to_dict_has_all_keys(self):
        from pipelines.lineage.rules import LineageEvent
        ev = LineageEvent("DELISTING", date(2024, 1, 1), 0.8, "SYM", None, "gone")
        d  = ev.to_dict()
        for key in ["symbol_from", "symbol_to", "event_date", "event_type",
                    "confidence", "reason", "corroborating_evidence"]:
            assert key in d

    def test_to_dict_event_date_is_iso_string(self):
        from pipelines.lineage.rules import LineageEvent
        ev = LineageEvent("LISTING", date(2024, 5, 28), 0.95)
        assert ev.to_dict()["event_date"] == "2024-05-28"


class TestTask7RulesEngine:

    def setup_method(self):
        from pipelines.lineage.rules import LineageRulesEngine
        self.engine = LineageRulesEngine()

    def test_detect_symbol_rename_basic(self):
        ev = self.engine.detect_symbol_rename("OLD", "NEW", date(2024, 1, 1))
        assert ev.event_type == "RENAME"
        assert ev.symbol_from == "OLD"
        assert ev.symbol_to   == "NEW"

    def test_detect_symbol_rename_same_name_high_confidence(self):
        ev = self.engine.detect_symbol_rename(
            "OLD", "NEW", date(2024, 1, 1),
            company_name="Infosys Limited",
            new_company_name="Infosys Limited",
        )
        assert ev.confidence >= 0.90

    def test_detect_symbol_rename_same_symbols_raises(self):
        with pytest.raises(ValueError):
            self.engine.detect_symbol_rename("SYM", "SYM", date(2024, 1, 1))

    def test_detect_company_rename_above_threshold(self):
        ev, score = self.engine.detect_company_rename(
            "Infosys Limited", "Infosys Ltd", date(2024, 1, 1), fuzzy_threshold=0.80
        )
        assert ev is not None
        assert ev.event_type == "RENAME"
        assert score >= 0.80

    def test_detect_company_rename_below_threshold(self):
        ev, score = self.engine.detect_company_rename(
            "Infosys Limited", "Wipro Technologies", date(2024, 1, 1)
        )
        assert ev is None
        assert score < 0.85

    def test_detect_company_rename_empty_name(self):
        ev, score = self.engine.detect_company_rename("", "Infosys", date(2024, 1, 1))
        assert ev is None
        assert score == 0.0

    def test_detect_merger_with_action(self):
        ev = self.engine.detect_merger_demerger(
            symbol_disappears=True, new_symbol_appears=True,
            old_symbol="ACME", new_symbol="BIGCO",
            event_date=date(2024, 1, 1),
            corporate_action={"action_code": "MERGER"},
        )
        assert ev.event_type == "MERGER"
        assert ev.confidence >= 0.90

    def test_detect_merger_without_action_lower_confidence(self):
        ev = self.engine.detect_merger_demerger(
            symbol_disappears=True, new_symbol_appears=False,
            old_symbol="ACME", new_symbol="ACME",
            event_date=date(2024, 1, 1),
        )
        assert ev.event_type == "MERGER"
        assert ev.confidence < 0.85

    def test_detect_demerger_type(self):
        ev = self.engine.detect_merger_demerger(
            symbol_disappears=False, new_symbol_appears=True,
            old_symbol="PARENT", new_symbol="CHILD",
            event_date=date(2024, 1, 1),
            corporate_action={"action_code": "DEMERGER"},
        )
        assert ev.event_type == "DEMERGER"

    def test_detect_delisting_explicit(self):
        ev = self.engine.detect_delisting("GONE", date(2024, 1, 1), is_explicit=True)
        assert ev.event_type   == "DELISTING"
        assert ev.symbol_from  == "GONE"
        assert ev.symbol_to    is None
        assert ev.confidence   >= 0.90

    def test_detect_delisting_inferred_lower_confidence(self):
        ev = self.engine.detect_delisting("GONE", date(2024, 1, 1), is_explicit=False)
        assert ev.confidence < 0.90

    def test_detect_relisting(self):
        ev = self.engine.detect_relisting("BACK", date(2024, 6, 1))
        assert ev.event_type  == "RELISTING"
        assert ev.symbol_to   == "BACK"
        assert ev.symbol_from is None

    def test_detect_suspension(self):
        ev = self.engine.detect_suspension("SUSP", date(2024, 3, 1), "regulatory")
        assert ev.event_type  == "SUSPENSION"
        assert ev.symbol_from == "SUSP"
        assert ev.confidence  >= 0.85


class TestTask7SymbolLinker:

    def setup_method(self):
        from pipelines.lineage.linker import SymbolLinker
        self.linker = SymbolLinker()

    def _make_snapshots(self):
        historical = pd.DataFrame([
            {"SYMBOL": "INFY",  "ISIN": "INE009A01021"},
            {"SYMBOL": "TCS",   "ISIN": "INE467B01029"},
            {"SYMBOL": "OLD",   "ISIN": "INE111X00000"},  # will be renamed
            {"SYMBOL": "GONE",  "ISIN": "INE222X00000"},  # will be delisted
        ])
        current = pd.DataFrame([
            {"SYMBOL": "INFY",  "ISIN": "INE009A01021"},
            {"SYMBOL": "TCS",   "ISIN": "INE467B01029"},
            {"SYMBOL": "NEW",   "ISIN": "INE111X00000"},  # same ISIN, new symbol
            {"SYMBOL": "FRESH", "ISIN": "INE333X00000"},  # new listing
        ])
        return historical, current

    def test_link_returns_dataframe(self):
        hist, curr = self._make_snapshots()
        df = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        assert isinstance(df, pd.DataFrame)

    def test_link_detects_new_listing(self):
        hist, curr = self._make_snapshots()
        df = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        listings = df[df["event_type"] == "LISTING"]
        assert "FRESH" in listings["symbol_to"].values

    def test_link_detects_delisting(self):
        hist, curr = self._make_snapshots()
        df = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        delistings = df[df["event_type"] == "DELISTING"]
        assert "GONE" in delistings["symbol_from"].values

    def test_link_detects_rename_via_isin(self):
        hist, curr = self._make_snapshots()
        df = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        renames = df[df["event_type"] == "RENAME"]
        assert len(renames) >= 1
        assert "OLD" in renames["symbol_from"].values
        assert "NEW" in renames["symbol_to"].values

    def test_link_no_false_positives_for_stable_symbols(self):
        hist, curr = self._make_snapshots()
        df = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        # INFY and TCS should not appear in any events
        assert "INFY" not in df["symbol_from"].fillna("").values
        assert "INFY" not in df["symbol_to"].fillna("").values

    def test_cross_reference_boosts_confidence_on_match(self):
        hist, curr = self._make_snapshots()
        events = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        actions = pd.DataFrame([
            {"SYMBOL": "GONE", "action_code": "DELISTING", "event_date": "2024-06-01"},
        ])
        original_conf = events[events["symbol_from"] == "GONE"]["confidence"].values[0]
        updated = self.linker.cross_reference_with_actions(events, actions)
        new_conf = updated[updated["symbol_from"] == "GONE"]["confidence"].values[0]
        assert new_conf >= original_conf
        assert updated[updated["symbol_from"] == "GONE"]["corroborated"].values[0] == True

    def test_cross_reference_flags_manual_review_without_action(self):
        hist, curr = self._make_snapshots()
        events  = self.linker.link_across_periods(curr, hist, date(2024, 6, 1))
        updated = self.linker.cross_reference_with_actions(events, pd.DataFrame())
        delistings = updated[updated["event_type"] == "DELISTING"]
        assert delistings["manual_review_required"].all()


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 8 — Adjustments
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask8Calculator:

    def test_split_1_for_2(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        assert AdjustmentCalculator.calculate_split_adjustment(1, 2) == 0.5

    def test_split_1_for_5(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        assert AdjustmentCalculator.calculate_split_adjustment(1, 5) == 0.2

    def test_reverse_split_greater_than_1(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        assert AdjustmentCalculator.calculate_split_adjustment(2, 1) == 2.0

    def test_split_zero_raises(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        with pytest.raises(ValueError):
            AdjustmentCalculator.calculate_split_adjustment(0, 2)

    def test_bonus_1_for_1(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        assert AdjustmentCalculator.calculate_bonus_adjustment(1, 1) == 0.5

    def test_bonus_1_for_2(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        result = AdjustmentCalculator.calculate_bonus_adjustment(2, 1)
        assert abs(result - (2 / 3)) < 1e-9

    def test_bonus_zero_raises(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        with pytest.raises(ValueError):
            AdjustmentCalculator.calculate_bonus_adjustment(0, 1)

    def test_cumulative_single_split(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        events = pd.DataFrame([
            {"action_code": "SPLIT", "old_value": 0.5, "event_date": "2024-01-01"},
        ])
        result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
        assert result["cumulative_split_adjustment"] == 0.5
        assert result["total_adjustment_factor"]     == 0.5

    def test_cumulative_split_then_bonus(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        events = pd.DataFrame([
            {"action_code": "SPLIT", "old_value": 0.5,  "event_date": "2023-01-01"},
            {"action_code": "BONUS", "old_value": 0.5,  "event_date": "2024-01-01"},
        ])
        result = AdjustmentCalculator.calculate_cumulative_adjustment(events)
        assert result["cumulative_split_adjustment"] == 0.5
        assert result["cumulative_bonus_adjustment"] == 0.5
        assert abs(result["total_adjustment_factor"] - 0.25) < 1e-9

    def test_cumulative_empty_returns_ones(self):
        from pipelines.adjustments.calculator import AdjustmentCalculator
        result = AdjustmentCalculator.calculate_cumulative_adjustment(pd.DataFrame(
            columns=["action_code", "old_value", "event_date"]
        ))
        assert result["total_adjustment_factor"] == 1.0


class TestTask8AdjustmentBuilder:

    def _make_actions(self):
        return pd.DataFrame([
            {"security_id": 1, "action_code": "SPLIT",
             "event_date": "2022-06-15", "old_value": 0.5},
            {"security_id": 1, "action_code": "BONUS",
             "event_date": "2023-09-01", "old_value": 0.5},
            {"security_id": 2, "action_code": "SPLIT",
             "event_date": "2023-01-10", "old_value": 0.5},
        ])

    def test_build_returns_dataframe(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            self._make_actions(), pd.DataFrame()
        )
        assert isinstance(df, pd.DataFrame)

    def test_build_has_required_columns(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            self._make_actions(), pd.DataFrame()
        )
        for col in ["security_id", "as_of_date", "total_adjustment_factor"]:
            assert col in df.columns

    def test_build_row_count(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            self._make_actions(), pd.DataFrame()
        )
        # 2 events for security 1, 1 event for security 2
        assert len(df) == 3

    def test_build_factors_positive(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            self._make_actions(), pd.DataFrame()
        )
        assert (df["total_adjustment_factor"] > 0).all()

    def test_build_cumulative_split_then_bonus(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            self._make_actions(), pd.DataFrame()
        )
        sec1 = df[df["security_id"] == 1].sort_values("as_of_date")
        # After split (0.5): total = 0.5
        assert sec1.iloc[0]["total_adjustment_factor"] == 0.5
        # After bonus (0.5): total = 0.5 × 0.5 = 0.25
        assert abs(sec1.iloc[1]["total_adjustment_factor"] - 0.25) < 1e-9

    def test_build_no_duplicate_security_date(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            self._make_actions(), pd.DataFrame()
        )
        assert not df.duplicated(subset=["security_id", "as_of_date"]).any()

    def test_build_ignores_dividend_actions(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        actions = pd.DataFrame([
            {"security_id": 1, "action_code": "DIVIDEND",
             "event_date": "2024-01-01", "old_value": 5.0},
        ])
        df = AdjustmentFactorBuilder().build_from_corporate_actions(
            actions, pd.DataFrame()
        )
        assert len(df) == 0   # DIVIDEND does not produce adjustment rows

    def test_build_missing_required_columns_raises(self):
        from pipelines.adjustments.adjuster import AdjustmentFactorBuilder
        bad = pd.DataFrame([{"symbol": "INFY", "value": 1.0}])
        with pytest.raises(ValueError, match="missing required columns"):
            AdjustmentFactorBuilder().build_from_corporate_actions(bad, pd.DataFrame())


# ═══════════════════════════════════════════════════════════════════════════════
# DATA VALIDATION — run against real staged / curated files
# ═══════════════════════════════════════════════════════════════════════════════

class Phase2Validator:
    """
    Validates real pipeline outputs in data/staging/ and data/curated/.
    Run via: python pipelines/phase2_validator.py
    (Not a pytest class — no test_ prefix methods.)
    """

    def validate_extraction(self) -> bool:
        """Raw staging files exist and are non-empty."""
        ok = True
        for fname in ["nse_symbols_consolidated.csv", "nse_actions_consolidated.csv"]:
            path = DATA_STAGING / fname
            if not path.exists() or path.stat().st_size == 0:
                print(f"  ✗ MISSING or EMPTY: {fname}")
                ok = False
            else:
                df = pd.read_csv(path)
                print(f"  ✓ {fname}: {len(df):,} rows")
        return ok

    def validate_normalization(self) -> bool:
        """Curated dimension files have correct columns and unique PKs."""
        ok = True
        checks = {
            "dim_security_master.csv": (["security_id", "nse_symbol", "isin"], "security_id"),
            "dim_issuer.csv":          (["issuer_id", "issuer_name"],          "issuer_id"),
        }
        for fname, (required_cols, pk) in checks.items():
            path = DATA_CURATED / fname
            if not path.exists():
                print(f"  ✗ MISSING: {fname}")
                ok = False
                continue
            df = pd.read_csv(path)
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                print(f"  ✗ {fname}: missing columns {missing}")
                ok = False
            elif df[pk].duplicated().any():
                print(f"  ✗ {fname}: duplicate {pk} values")
                ok = False
            else:
                print(f"  ✓ {fname}: {len(df):,} rows, PK clean")
        return ok

    def validate_lineage(self) -> bool:
        """Lineage events are chronologically ordered and have valid confidence."""
        path = DATA_CURATED / "fact_symbol_lineage_event.csv"
        if not path.exists():
            print(f"  ✗ MISSING: fact_symbol_lineage_event.csv")
            return False
        df = pd.read_csv(path)
        ok = True
        if (df["confidence"] < 0).any() or (df["confidence"] > 1).any():
            print("  ✗ lineage: confidence values out of [0, 1]")
            ok = False
        # No symbol appearing in both symbol_from and symbol_to in the same event
        self_loops = df[df["symbol_from"] == df["symbol_to"]].dropna()
        if not self_loops.empty:
            print(f"  ✗ lineage: {len(self_loops)} self-loop events (from == to)")
            ok = False
        if ok:
            print(f"  ✓ fact_symbol_lineage_event.csv: {len(df):,} rows, valid")
        return ok

    def validate_adjustments(self) -> bool:
        """Adjustment factors are all positive and internally consistent."""
        path = DATA_CURATED / "fact_adjustment_factor.csv"
        if not path.exists():
            print(f"  ✗ MISSING: fact_adjustment_factor.csv")
            return False
        df = pd.read_csv(path)
        ok = True
        for col in ["cumulative_split_adjustment", "total_adjustment_factor"]:
            if col in df.columns and (df[col] <= 0).any():
                print(f"  ✗ adjustments: non-positive values in {col}")
                ok = False
        if ok:
            print(f"  ✓ fact_adjustment_factor.csv: {len(df):,} rows, factors valid")
        return ok

    def cross_validate_all(self) -> bool:
        """Every security_id in adjustments/lineage exists in dim_security_master."""
        master_path = DATA_CURATED / "dim_security_master.csv"
        if not master_path.exists():
            print("  ✗ cross-validate: dim_security_master.csv not found")
            return False
        master_ids = set(pd.read_csv(master_path)["security_id"].dropna())
        ok = True
        for fname in ["fact_adjustment_factor.csv", "fact_symbol_lineage_event.csv"]:
            path = DATA_CURATED / fname
            if not path.exists():
                continue
            df = pd.read_csv(path)
            if "security_id" not in df.columns:
                continue
            orphans = set(df["security_id"].dropna()) - master_ids
            if orphans:
                print(f"  ✗ {fname}: {len(orphans)} security_ids not in master")
                ok = False
            else:
                print(f"  ✓ {fname}: all security_ids resolve")
        return ok


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point for data validation
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("\n" + "=" * 60)
    print("Phase 2 Data Validation")
    print("=" * 60)

    v = Phase2Validator()
    checks = [
        ("Extraction",    v.validate_extraction),
        ("Normalization", v.validate_normalization),
        ("Lineage",       v.validate_lineage),
        ("Adjustments",   v.validate_adjustments),
        ("Cross-validate", v.cross_validate_all),
    ]

    results = []
    for name, fn in checks:
        print(f"\n{name}:")
        try:
            results.append((name, fn()))
        except Exception as exc:
            print(f"  ✗ ERROR: {exc}")
            results.append((name, False))

    print("\n" + "=" * 60)
    for name, passed in results:
        print(f"  {'✅' if passed else '❌'} {name}")
    print()
    sys.exit(0 if all(r for _, r in results) else 1)
