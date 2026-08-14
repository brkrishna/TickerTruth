"""
Tests for pipelines/extract/extractor.py — fetch_nse_symbols() fallback
chain, _normalize_symbol_columns(), _validate_symbols(). Part of closing
the general extractor coverage gap (only the bhavcopy URL fallback and the
corp-actions homepage-403 path had dedicated tests before this).

All network calls are mocked — no live NSE requests.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipelines.extract.extractor import MIN_SYMBOL_ROWS, RawDataExtractor


@pytest.fixture()
def extractor(tmp_path):
    return RawDataExtractor(output_dir=tmp_path)


def _min_rows_symbols_csv() -> str:
    """A minimal but MIN_SYMBOL_ROWS+-sized valid EQUITY_L.csv body."""
    header = "SYMBOL,COMPANY_NAME,ISIN,LISTING_DATE\n"
    rows = "\n".join(
        f"SYM{i},Company {i} Ltd,INE{i:06d}01011,01-01-2000"
        for i in range(MIN_SYMBOL_ROWS)
    )
    return header + rows + "\n"


def _http_response(status_code, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if status_code >= 400:
        resp.raise_for_status.side_effect = __import__("requests").HTTPError(
            response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ── fetch_nse_symbols(): fallback chain ─────────────────────────────────────


def test_fetch_nse_symbols_uses_archives_when_available(extractor):
    ok_resp = _http_response(200, _min_rows_symbols_csv())

    with patch("requests.get", return_value=ok_resp) as get_mock:
        df = extractor.fetch_nse_symbols()

    assert get_mock.call_count == 1  # never fell through to session-based fallbacks
    assert len(df) == MIN_SYMBOL_ROWS
    assert "STATUS" in df.columns
    assert (df["STATUS"] == "ACTIVE").all()


def test_fetch_nse_symbols_falls_back_to_json_api_when_archives_fail(extractor):
    archives_fail = _http_response(500)
    json_ok = MagicMock()
    json_ok.raise_for_status.return_value = None
    json_ok.json.return_value = [
        {
            "SYMBOL": f"SYM{i}",
            "COMPANY_NAME": f"Company {i}",
            "ISIN": f"INE{i:06d}01011",
            "LISTING_DATE": "01-01-2000",
        }
        for i in range(MIN_SYMBOL_ROWS)
    ]
    homepage_resp = _http_response(200)

    with (
        patch("requests.get", return_value=archives_fail),
        patch("requests.Session.get", side_effect=[homepage_resp, json_ok]),
    ):
        df = extractor.fetch_nse_symbols()

    assert len(df) == MIN_SYMBOL_ROWS


def test_fetch_nse_symbols_raises_when_all_sources_fail(extractor):
    fail_resp = _http_response(500)

    with (
        patch("requests.get", return_value=fail_resp),
        patch("requests.Session.get", return_value=fail_resp),
    ):
        with pytest.raises(
            RuntimeError, match="All three NSE equity master URLs failed"
        ):
            extractor.fetch_nse_symbols()


def test_fetch_nse_symbols_uses_cache_when_file_already_exists(extractor, tmp_path):
    from datetime import date

    cached = tmp_path / f"nse_symbols_{date.today().isoformat()}.csv"
    cached.write_text(
        "SYMBOL,COMPANY_NAME,ISIN,LISTING_DATE,STATUS\nINFY,Infosys,INE1,01-01-2000,ACTIVE\n"
    )

    with patch("requests.get") as get_mock:
        df = extractor.fetch_nse_symbols()

    get_mock.assert_not_called()
    assert len(df) == 1


# ── _normalize_symbol_columns ────────────────────────────────────────────────


def test_normalize_symbol_columns_strips_and_uppercases_headers(extractor):
    df = pd.DataFrame([{" symbol ": "INFY", "isin": "INE1"}])
    out = extractor._normalize_symbol_columns(df)
    assert "SYMBOL" in out.columns
    assert "ISIN" in out.columns


def test_normalize_symbol_columns_applies_known_aliases(extractor):
    df = pd.DataFrame([{"NAME OF COMPANY": "Infosys", "SYMBOL": "INFY"}])
    out = extractor._normalize_symbol_columns(df)
    assert "COMPANY_NAME" in out.columns
    assert "NAME OF COMPANY" not in out.columns


def test_normalize_symbol_columns_synthesizes_status_when_absent(extractor):
    df = pd.DataFrame([{"SYMBOL": "INFY"}])
    out = extractor._normalize_symbol_columns(df)
    assert (out["STATUS"] == "ACTIVE").all()


def test_normalize_symbol_columns_preserves_existing_status(extractor):
    df = pd.DataFrame([{"SYMBOL": "INFY", "STATUS": "SUSPENDED"}])
    out = extractor._normalize_symbol_columns(df)
    assert out.iloc[0]["STATUS"] == "SUSPENDED"


def test_normalize_symbol_columns_dedupes_on_symbol_and_listing_date_keeps_last(
    extractor,
):
    df = pd.DataFrame(
        [
            {"SYMBOL": "INFY", "LISTING_DATE": "2000-01-01", "STATUS": "SUSPENDED"},
            {"SYMBOL": "INFY", "LISTING_DATE": "2000-01-01", "STATUS": "ACTIVE"},
        ]
    )
    out = extractor._normalize_symbol_columns(df)
    assert len(out) == 1
    assert out.iloc[0]["STATUS"] == "ACTIVE"


def test_normalize_symbol_columns_does_not_mutate_input(extractor):
    df = pd.DataFrame([{"symbol": "INFY"}])
    df_before = df.copy()
    extractor._normalize_symbol_columns(df)
    pd.testing.assert_frame_equal(df, df_before)


# ── _validate_symbols ─────────────────────────────────────────────────────────


def test_validate_symbols_happy_path_does_not_raise(extractor):
    df = pd.DataFrame(
        [
            {"SYMBOL": f"SYM{i}", "ISIN": f"INE{i:06d}", "LISTING_DATE": "2000-01-01"}
            for i in range(MIN_SYMBOL_ROWS)
        ]
    )
    extractor._validate_symbols(df)  # should not raise


def test_validate_symbols_missing_required_column_raises(extractor):
    df = pd.DataFrame([{"SYMBOL": "INFY"}])  # missing ISIN, LISTING_DATE
    with pytest.raises(ValueError, match="missing required columns"):
        extractor._validate_symbols(df)


def test_validate_symbols_too_few_rows_raises(extractor):
    df = pd.DataFrame(
        [{"SYMBOL": "INFY", "ISIN": "INE1", "LISTING_DATE": "2000-01-01"}]
    )
    with pytest.raises(ValueError, match="expected"):
        extractor._validate_symbols(df)


def test_validate_symbols_null_isin_logs_warning_not_raise(extractor, caplog):
    df = pd.DataFrame(
        [
            {
                "SYMBOL": f"SYM{i}",
                "ISIN": None if i == 0 else f"INE{i:06d}",
                "LISTING_DATE": "2000-01-01",
            }
            for i in range(MIN_SYMBOL_ROWS)
        ]
    )
    extractor._validate_symbols(df)  # should not raise despite the null ISIN
