"""
Tests for RawToCanonicalMapper.map_to_fact_equity_eod() (pipelines/normalize/normalizer.py).

Added 2026-08-14 alongside the INFRA-2 bhavcopy fix — this closes the gap
where fetch_bhavcopy() worked but nothing mapped its output to
fact_equity_eod. All tests use inline DataFrames — no file I/O, no
network calls.
"""

import pandas as pd
import pytest

from pipelines.normalize.normalizer import RawToCanonicalMapper


@pytest.fixture()
def mapper():
    return RawToCanonicalMapper(source_file="bhavcopy_consolidated.csv")


def _dim_security_master() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"security_id": 1, "nse_symbol": "INFY"},
            {"security_id": 2, "nse_symbol": "TCS"},
        ]
    )


def _raw_bhavcopy(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ── happy path ────────────────────────────────────────────────────────────────


def test_map_to_fact_equity_eod_happy_path(mapper):
    raw = _raw_bhavcopy(
        [
            {
                "SYMBOL": "INFY",
                "SERIES": "EQ",
                "OPEN": 1500.0,
                "HIGH": 1520.0,
                "LOW": 1490.0,
                "CLOSE": 1510.0,
                "TOTTRDQTY": 1000000,
                "TIMESTAMP": "2026-08-13",
            },
            {
                "SYMBOL": "TCS",
                "SERIES": "EQ",
                "OPEN": 3500.0,
                "HIGH": 3550.0,
                "LOW": 3480.0,
                "CLOSE": 3520.0,
                "TOTTRDQTY": 500000,
                "TIMESTAMP": "2026-08-13",
            },
        ]
    )

    out = mapper.map_to_fact_equity_eod(raw, _dim_security_master())

    assert len(out) == 2
    assert set(out.columns) >= {
        "security_id",
        "trading_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    }
    infy = out[out["security_id"] == 1].iloc[0]
    assert infy["trading_date"] == "2026-08-13"
    assert infy["close_price"] == 1510.0
    assert infy["volume"] == 1000000


def test_map_to_fact_equity_eod_accepts_legacy_bhavcopy_date_format(mapper):
    raw = _raw_bhavcopy(
        [
            {
                "SYMBOL": "INFY",
                "OPEN": 1500.0,
                "HIGH": 1520.0,
                "LOW": 1490.0,
                "CLOSE": 1510.0,
                "TOTTRDQTY": 1000000,
                "TIMESTAMP": "13-AUG-2026",  # legacy bhavcopy format
            }
        ]
    )

    out = mapper.map_to_fact_equity_eod(raw, _dim_security_master())

    assert out.iloc[0]["trading_date"] == "2026-08-13"


# ── edge cases ───────────────────────────────────────────────────────────────


def test_map_to_fact_equity_eod_empty_dataframe(mapper):
    raw = pd.DataFrame(columns=["SYMBOL", "OPEN", "HIGH", "LOW", "CLOSE", "TIMESTAMP"])

    out = mapper.map_to_fact_equity_eod(raw, _dim_security_master())

    assert len(out) == 0
    assert "security_id" in out.columns


def test_map_to_fact_equity_eod_flags_unresolved_symbol(mapper):
    raw = _raw_bhavcopy(
        [
            {
                "SYMBOL": "NOTLISTED",
                "OPEN": 10.0,
                "HIGH": 11.0,
                "LOW": 9.0,
                "CLOSE": 10.5,
                "TOTTRDQTY": 100,
                "TIMESTAMP": "2026-08-13",
            }
        ]
    )

    out = mapper.map_to_fact_equity_eod(raw, _dim_security_master())

    assert len(out) == 1
    assert pd.isna(out.iloc[0]["security_id"])
    assert "UNRESOLVED_SYMBOL" in out.iloc[0]["_quality_issues"]


def test_map_to_fact_equity_eod_retains_unparseable_date_row(mapper):
    """Rows with a bad date are flagged and retained, never dropped silently."""
    raw = _raw_bhavcopy(
        [
            {
                "SYMBOL": "INFY",
                "OPEN": 1500.0,
                "HIGH": 1520.0,
                "LOW": 1490.0,
                "CLOSE": 1510.0,
                "TOTTRDQTY": 1000000,
                "TIMESTAMP": "not-a-date",
            }
        ]
    )

    out = mapper.map_to_fact_equity_eod(raw, _dim_security_master())

    assert len(out) == 1
    assert pd.isna(out.iloc[0]["trading_date"])
    assert out.iloc[0]["normalization_error"] == "UNPARSEABLE_TRADE_DATE"


# ── invalid input ────────────────────────────────────────────────────────────


def test_map_to_fact_equity_eod_raises_on_missing_required_columns(mapper):
    raw = pd.DataFrame([{"SYMBOL": "INFY"}])  # missing TIMESTAMP, CLOSE

    with pytest.raises(ValueError, match="missing required columns"):
        mapper.map_to_fact_equity_eod(raw, _dim_security_master())
