"""
Tests for pipelines/normalize/normalizer.py (RawToCanonicalMapper) —
map_to_dim_issuer, map_to_dim_security_master, map_to_fact_corporate_action_event.

Closes the NSE core normalize test gap (session of 2026-08-14). Only
map_to_fact_equity_eod() had a dedicated test file before this
(tests/test_normalize_equity_eod.py) — these three mappers, the module's
original core, had none.

All tests are pure — no I/O, no network calls.
"""

import pandas as pd
import pytest

from pipelines.normalize.normalizer import RawToCanonicalMapper


@pytest.fixture()
def mapper():
    return RawToCanonicalMapper(source_file="nse_symbols_consolidated.csv")


# ── map_to_dim_issuer ────────────────────────────────────────────────────────


def test_map_to_dim_issuer_happy_path(mapper):
    raw = pd.DataFrame(
        [
            {"SYMBOL": "INFY", "COMPANY_NAME": "Infosys Ltd", "SECTOR": "IT"},
            {
                "SYMBOL": "TCS",
                "COMPANY_NAME": "Tata Consultancy Services Ltd",
                "SECTOR": "IT",
            },
        ]
    )
    out = mapper.map_to_dim_issuer(raw)

    assert len(out) == 2
    assert set(out["issuer_name"]) == {
        "INFOSYS LIMITED",
        "TATA CONSULTANCY SERVICES LIMITED",
    }
    assert list(out["issuer_id"]) == [1, 2]
    assert (out["country"] == "India").all()
    assert set(out["sector"]) == {"IT"}


def test_map_to_dim_issuer_deduplicates_same_normalized_name(mapper):
    raw = pd.DataFrame(
        [
            {"SYMBOL": "A", "COMPANY_NAME": "Acme Industries Ltd"},
            {"SYMBOL": "B", "COMPANY_NAME": "Acme Industries Limited"},
        ]
    )
    out = mapper.map_to_dim_issuer(raw)

    # Both raw names normalize to "ACME INDUSTRIES LIMITED" -> one issuer row
    assert len(out) == 1


def test_map_to_dim_issuer_empty_dataframe(mapper):
    raw = pd.DataFrame(columns=["SYMBOL", "COMPANY_NAME", "SECTOR"])
    out = mapper.map_to_dim_issuer(raw)

    assert out.empty
    for col in ["issuer_id", "issuer_name", "sector", "market_cap_category", "country"]:
        assert col in out.columns


def test_map_to_dim_issuer_missing_name_column_raises(mapper):
    raw = pd.DataFrame([{"SYMBOL": "INFY"}])
    with pytest.raises(ValueError, match="no company name column"):
        mapper.map_to_dim_issuer(raw)


def test_map_to_dim_issuer_no_sector_column_defaults_to_none(mapper):
    raw = pd.DataFrame([{"SYMBOL": "INFY", "COMPANY_NAME": "Infosys Ltd"}])
    out = mapper.map_to_dim_issuer(raw)
    assert out.iloc[0]["sector"] is None


def test_map_to_dim_issuer_does_not_mutate_input(mapper):
    raw = pd.DataFrame([{"SYMBOL": "INFY", "COMPANY_NAME": "Infosys Ltd"}])
    raw_before = raw.copy()
    mapper.map_to_dim_issuer(raw)
    pd.testing.assert_frame_equal(raw, raw_before)


# ── map_to_dim_security_master ───────────────────────────────────────────────


def _dim_issuer_for(names: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"issuer_id": i + 1, "issuer_name": name} for i, name in enumerate(names)]
    )


def test_map_to_dim_security_master_happy_path(mapper):
    raw = pd.DataFrame(
        [
            {
                "SYMBOL": "INFY-EQ",
                "COMPANY_NAME": "Infosys Ltd",
                "ISIN": "ine009a01021",
                "LISTING_DATE": "28-05-1993",
                "STATUS": "ACTIVE",
            }
        ]
    )
    dim_issuer = _dim_issuer_for(["INFOSYS LIMITED"])

    out = mapper.map_to_dim_security_master(raw, dim_issuer)

    row = out.iloc[0]
    assert row["nse_symbol"] == "INFY"  # -EQ suffix stripped
    assert row["isin"] == "INE009A01021"  # uppercased
    assert row["issuer_id"] == 1
    assert row["listing_date"] == "1993-05-28"
    assert row["active_flag"] == True  # noqa: E712
    assert row["exchange_id"] == 1


def test_map_to_dim_security_master_delisted_status_sets_active_flag_false(mapper):
    raw = pd.DataFrame(
        [{"SYMBOL": "GONE", "COMPANY_NAME": "Gone Ltd", "STATUS": "DELISTED"}]
    )
    dim_issuer = _dim_issuer_for(["GONE LIMITED"])

    out = mapper.map_to_dim_security_master(raw, dim_issuer)

    assert out.iloc[0]["active_flag"] == False  # noqa: E712


def test_map_to_dim_security_master_flags_unresolved_issuer(mapper):
    raw = pd.DataFrame([{"SYMBOL": "ORPHAN", "COMPANY_NAME": "Nobody Knows This Co"}])
    dim_issuer = _dim_issuer_for(["SOMEONE ELSE LIMITED"])

    out = mapper.map_to_dim_security_master(raw, dim_issuer)

    assert pd.isna(out.iloc[0]["issuer_id"])
    assert "UNRESOLVED_SYMBOL" in out.iloc[0]["_quality_issues"]


def test_map_to_dim_security_master_deduplicates_symbol_keeping_last(mapper):
    raw = pd.DataFrame(
        [
            {"SYMBOL": "INFY", "COMPANY_NAME": "Infosys Ltd", "STATUS": "SUSPENDED"},
            {"SYMBOL": "INFY", "COMPANY_NAME": "Infosys Ltd", "STATUS": "ACTIVE"},
        ]
    )
    dim_issuer = _dim_issuer_for(["INFOSYS LIMITED"])

    out = mapper.map_to_dim_security_master(raw, dim_issuer)

    assert len(out) == 1
    assert out.iloc[0]["active_flag"] == True  # noqa: E712  (last row wins)


def test_map_to_dim_security_master_empty_dataframe(mapper):
    raw = pd.DataFrame(
        columns=["SYMBOL", "COMPANY_NAME", "ISIN", "LISTING_DATE", "STATUS"]
    )
    dim_issuer = pd.DataFrame(columns=["issuer_id", "issuer_name"])

    out = mapper.map_to_dim_security_master(raw, dim_issuer)

    assert out.empty
    for col in [
        "security_id",
        "nse_symbol",
        "isin",
        "company_name",
        "issuer_id",
        "exchange_id",
        "listing_date",
        "active_flag",
    ]:
        assert col in out.columns


def test_map_to_dim_security_master_missing_symbol_column_raises(mapper):
    raw = pd.DataFrame([{"COMPANY_NAME": "Infosys Ltd"}])
    with pytest.raises(ValueError, match="missing SYMBOL"):
        mapper.map_to_dim_security_master(raw, pd.DataFrame())


def test_map_to_dim_security_master_does_not_mutate_inputs(mapper):
    raw = pd.DataFrame(
        [{"SYMBOL": "INFY", "COMPANY_NAME": "Infosys Ltd", "STATUS": "ACTIVE"}]
    )
    dim_issuer = _dim_issuer_for(["INFOSYS LIMITED"])
    raw_before, dim_issuer_before = raw.copy(), dim_issuer.copy()

    mapper.map_to_dim_security_master(raw, dim_issuer)

    pd.testing.assert_frame_equal(raw, raw_before)
    pd.testing.assert_frame_equal(dim_issuer, dim_issuer_before)


# ── map_to_fact_corporate_action_event ──────────────────────────────────────


def _dim_security_for(symbols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"security_id": i + 1, "nse_symbol": s} for i, s in enumerate(symbols)]
    )


def test_map_to_fact_corporate_action_event_happy_path(mapper):
    raw = pd.DataFrame(
        [
            {
                "SYMBOL": "INFY",
                "ACTION_TYPE_RAW": "Dividend - Rs 5 Per Share",
                "EX_DATE": "15-06-2026",
                "RECORD_DATE": "16-06-2026",
                "PAYMENT_DATE": "30-06-2026",
                "FACE_VALUE": "5",
            }
        ]
    )
    dim_security = _dim_security_for(["INFY"])

    out = mapper.map_to_fact_corporate_action_event(raw, dim_security)

    row = out.iloc[0]
    assert row["security_id"] == 1
    assert row["action_code"] == "DIVIDEND"
    assert row["event_date"] == "2026-06-15"
    assert row["record_date"] == "2026-06-16"
    assert row["payment_date"] == "2026-06-30"
    assert row["old_value"] == pytest.approx(5.0)
    assert row["confidence_score"] == 1.0
    assert row["confidence_flag"] == "HIGH"


def test_map_to_fact_corporate_action_event_bonus_old_value_is_ratio_not_face_value(
    mapper,
):
    # old_value must be the price adjustment factor parsed from the ratio in
    # the action text (existing / (existing + bonus)), not FACE_VALUE — two
    # securities can both have "Bonus 1:1" with different face values and
    # must get the same old_value.
    raw = pd.DataFrame(
        [
            {
                "SYMBOL": "INFY",
                "ACTION_TYPE_RAW": "Bonus 1:1",
                "EX_DATE": "15-06-2026",
                "FACE_VALUE": "10",
            }
        ]
    )
    dim_security = _dim_security_for(["INFY"])

    out = mapper.map_to_fact_corporate_action_event(raw, dim_security)

    row = out.iloc[0]
    assert row["action_code"] == "BONUS"
    assert row["old_value"] == pytest.approx(0.5)


def test_map_to_fact_corporate_action_event_split_old_value_is_ratio_not_face_value(
    mapper,
):
    raw = pd.DataFrame(
        [
            {
                "SYMBOL": "INFY",
                "ACTION_TYPE_RAW": "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share",
                "EX_DATE": "15-06-2026",
                "FACE_VALUE": "2",
            }
        ]
    )
    dim_security = _dim_security_for(["INFY"])

    out = mapper.map_to_fact_corporate_action_event(raw, dim_security)

    row = out.iloc[0]
    assert row["action_code"] == "SPLIT"
    assert row["old_value"] == pytest.approx(0.2)


def test_map_to_fact_corporate_action_event_flags_unresolved_symbol(mapper):
    raw = pd.DataFrame(
        [
            {
                "SYMBOL": "NOTLISTED",
                "ACTION_TYPE_RAW": "Dividend",
                "EX_DATE": "15-06-2026",
            }
        ]
    )
    dim_security = _dim_security_for(["INFY"])

    out = mapper.map_to_fact_corporate_action_event(raw, dim_security)

    assert pd.isna(out.iloc[0]["security_id"])
    assert "UNRESOLVED_SYMBOL" in out.iloc[0]["_quality_issues"]


def test_map_to_fact_corporate_action_event_unknown_action_type_flagged(mapper):
    raw = pd.DataFrame(
        [
            {
                "SYMBOL": "INFY",
                "ACTION_TYPE_RAW": "Some Totally New Thing",
                "EX_DATE": "15-06-2026",
            }
        ]
    )
    dim_security = _dim_security_for(["INFY"])

    out = mapper.map_to_fact_corporate_action_event(raw, dim_security)

    assert out.iloc[0]["action_code"] == "UNKNOWN"
    assert "UNKNOWN_ACTION_TYPE" in out.iloc[0]["_quality_issues"]
    assert out.iloc[0]["confidence_flag"] in ("LOW", "MEDIUM")


def test_map_to_fact_corporate_action_event_empty_dataframe(mapper):
    raw = pd.DataFrame(columns=["SYMBOL", "ACTION_TYPE_RAW", "EX_DATE"])
    dim_security = pd.DataFrame(columns=["security_id", "nse_symbol"])

    out = mapper.map_to_fact_corporate_action_event(raw, dim_security)

    assert out.empty
    for col in ["security_id", "action_code", "event_date", "confidence_score"]:
        assert col in out.columns


def test_map_to_fact_corporate_action_event_missing_required_columns_raises(mapper):
    raw = pd.DataFrame([{"SYMBOL": "INFY"}])  # missing ACTION_TYPE_RAW, EX_DATE
    with pytest.raises(ValueError, match="missing required columns"):
        mapper.map_to_fact_corporate_action_event(raw, pd.DataFrame())


def test_map_to_fact_corporate_action_event_does_not_mutate_inputs(mapper):
    raw = pd.DataFrame(
        [{"SYMBOL": "INFY", "ACTION_TYPE_RAW": "Dividend", "EX_DATE": "15-06-2026"}]
    )
    dim_security = _dim_security_for(["INFY"])
    raw_before, dim_security_before = raw.copy(), dim_security.copy()

    mapper.map_to_fact_corporate_action_event(raw, dim_security)

    pd.testing.assert_frame_equal(raw, raw_before)
    pd.testing.assert_frame_equal(dim_security, dim_security_before)
