"""
Tests for RawDataExtractor bhavcopy fetching (INFRA-2 residual fix,
2026-08-14): NSE migrated bhavcopy to a new "UDiFF" URL/format that the
legacy `archives.nseindia.com` URL doesn't serve for current dates.

- _bhavcopy_urls() returns the new-format URL before the legacy one.
- fetch_bhavcopy() falls back to the legacy URL on a 404 from the new one.
- _normalize_bhavcopy_columns() maps UDiFF column names to the canonical
  contract (SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, LAST, PREVCLOSE,
  TOTTRDQTY, TOTTRDVAL, TIMESTAMP, TOTALTRADES, ISIN).

All tests are pure — no live network calls.
"""

import zipfile
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipelines.extract.extractor import RawDataExtractor


@pytest.fixture()
def extractor(tmp_path):
    return RawDataExtractor(output_dir=tmp_path)


def _zip_csv(filename: str, csv_text: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, csv_text)
    return buf.getvalue()


def _http_response(status_code, content=b""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    if status_code >= 400:
        err = MagicMock()
        err.response = resp
        resp.raise_for_status.side_effect = __import__("requests").HTTPError(
            response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ── _bhavcopy_urls() ordering ────────────────────────────────────────────────


def test_bhavcopy_urls_tries_new_format_first(extractor):
    urls = extractor._bhavcopy_urls(date(2026, 8, 13))
    assert len(urls) == 2
    assert (
        "nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20260813" in urls[0]
    )
    assert (
        "archives.nseindia.com/content/historical/EQUITIES/2026/AUG/cm13AUG2026bhav.csv.zip"
        in urls[1]
    )


# ── fetch_bhavcopy() fallback behavior ──────────────────────────────────────


def _new_format_csv():
    return (
        "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,"
        "OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,TtlTradgVol,"
        "TtlTrfVal,TtlNbOfTxsExctd\n"
        "2026-08-13,2026-08-13,CM,NSE,STK,1,INE001A01036,INFY,EQ,"
        "1500,1520,1490,1510,1510,1495,1000000,1500000000,5000\n"
    )


def test_fetch_bhavcopy_uses_new_format_when_available(extractor, monkeypatch):
    zip_bytes = _zip_csv("BhavCopy_NSE_CM_0_0_0_20260813_F_0000.csv", _new_format_csv())
    ok_resp = _http_response(200, zip_bytes)

    # Row-count/OHLC validation is covered separately; this fixture is a
    # single-row sample so it doesn't need to satisfy the ≥500 row minimum.
    monkeypatch.setattr(extractor, "_validate_bhavcopy", lambda df, d: None)

    with patch("requests.get", return_value=ok_resp) as get_mock:
        df = extractor.fetch_bhavcopy(date(2026, 8, 13))

    assert get_mock.call_count == 1
    assert list(df["SYMBOL"]) == ["INFY"]
    assert list(df["CLOSE"]) == [1510]
    assert "TOTTRDQTY" in df.columns and df["TOTTRDQTY"].iloc[0] == 1000000


def test_fetch_bhavcopy_falls_back_to_legacy_on_404(extractor, monkeypatch):
    legacy_csv = (
        "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,"
        "TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN\n"
        "INFY,EQ,1500,1520,1490,1510,1510,1495,1000000,1500000000,"
        "10-MAY-2024,5000,INE001A01036\n"
    )
    zip_bytes = _zip_csv("cm10MAY2024bhav.csv", legacy_csv)

    responses = [_http_response(404), _http_response(200, zip_bytes)]
    monkeypatch.setattr(extractor, "_validate_bhavcopy", lambda df, d: None)

    with patch("requests.get", side_effect=responses) as get_mock:
        df = extractor.fetch_bhavcopy(date(2024, 5, 10))

    assert get_mock.call_count == 2
    assert list(df["SYMBOL"]) == ["INFY"]


def test_fetch_bhavcopy_raises_when_both_formats_404(extractor):
    responses = [_http_response(404), _http_response(404)]

    with patch("requests.get", side_effect=responses):
        with pytest.raises(RuntimeError, match="not found"):
            extractor.fetch_bhavcopy(date(2099, 1, 1))


# ── _normalize_bhavcopy_columns() UDiFF mapping ─────────────────────────────


def test_normalize_bhavcopy_columns_maps_udiff_names(extractor):
    df = pd.DataFrame(
        {
            "TckrSymb": ["INFY"],
            "SctySrs": ["EQ"],
            "OpnPric": [1500.0],
            "HghPric": [1520.0],
            "LwPric": [1490.0],
            "ClsPric": [1510.0],
            "LastPric": [1510.0],
            "PrvsClsgPric": [1495.0],
            "TtlTradgVol": [1000000],
            "TtlTrfVal": [1500000000.0],
            "TtlNbOfTxsExctd": [5000],
            "TradDt": ["2026-08-13"],
            "ISIN": ["INE001A01036"],
        }
    )

    out = extractor._normalize_bhavcopy_columns(df)

    for col in [
        "SYMBOL",
        "SERIES",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "LAST",
        "PREVCLOSE",
        "TOTTRDQTY",
        "TOTTRDVAL",
        "TOTALTRADES",
        "TIMESTAMP",
        "ISIN",
    ]:
        assert col in out.columns, f"missing canonical column {col}"
    assert out["SYMBOL"].iloc[0] == "INFY"
    assert out["CLOSE"].iloc[0] == 1510.0
