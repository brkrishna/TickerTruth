"""
Tests for pipelines/extract/extractor.py — _normalize_corp_actions_columns(),
_validate_corp_actions(), _date_chunks(), _fetch_corp_actions_api(). Part of
closing the general extractor coverage gap; test_extract_corp_actions_blocking.py
already covers the homepage-403/Playwright-fallback control flow, not these
lower-level pure/near-pure helpers.

All network calls are mocked — no live NSE requests.
"""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pipelines.extract.extractor import RawDataExtractor


@pytest.fixture()
def extractor(tmp_path):
    return RawDataExtractor(output_dir=tmp_path)


# ── _date_chunks ──────────────────────────────────────────────────────────────


def test_date_chunks_splits_range_into_chunk_size_windows(extractor):
    chunks = list(extractor._date_chunks(date(2026, 1, 1), date(2026, 3, 1), 30))
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 30))
    assert chunks[-1][1] == date(2026, 3, 1)
    # windows are contiguous, no gaps or overlaps
    for (_, prev_end), (next_start, _) in zip(chunks, chunks[1:]):
        assert next_start == prev_end + pd.Timedelta(days=1).to_pytimedelta()


def test_date_chunks_single_day_range_yields_one_chunk(extractor):
    chunks = list(extractor._date_chunks(date(2026, 1, 1), date(2026, 1, 1), 30))
    assert chunks == [(date(2026, 1, 1), date(2026, 1, 1))]


def test_date_chunks_range_shorter_than_chunk_size_yields_one_chunk(extractor):
    chunks = list(extractor._date_chunks(date(2026, 1, 1), date(2026, 1, 10), 30))
    assert chunks == [(date(2026, 1, 1), date(2026, 1, 10))]


# ── _fetch_corp_actions_api ──────────────────────────────────────────────────


def test_fetch_corp_actions_api_returns_dataframe_from_list_response(extractor):
    session = MagicMock()
    session.get.return_value.raise_for_status.return_value = None
    session.get.return_value.json.return_value = [
        {"symbol": "INFY", "subject": "Dividend"}
    ]

    df = extractor._fetch_corp_actions_api(session, date(2026, 1, 1), date(2026, 1, 31))

    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "INFY"


def test_fetch_corp_actions_api_returns_dataframe_from_wrapped_dict_response(extractor):
    session = MagicMock()
    session.get.return_value.raise_for_status.return_value = None
    session.get.return_value.json.return_value = {"data": [{"symbol": "TCS"}]}

    df = extractor._fetch_corp_actions_api(session, date(2026, 1, 1), date(2026, 1, 31))

    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "TCS"


def test_fetch_corp_actions_api_returns_empty_df_on_zero_records(extractor):
    session = MagicMock()
    session.get.return_value.raise_for_status.return_value = None
    session.get.return_value.json.return_value = []

    df = extractor._fetch_corp_actions_api(session, date(2026, 1, 1), date(2026, 1, 31))

    assert df is not None
    assert df.empty


def test_fetch_corp_actions_api_returns_none_on_request_exception(extractor):
    import requests

    session = MagicMock()
    session.get.side_effect = requests.exceptions.Timeout("timed out")

    df = extractor._fetch_corp_actions_api(session, date(2026, 1, 1), date(2026, 1, 31))

    assert df is None


def test_fetch_corp_actions_api_returns_none_on_unexpected_json_type(extractor):
    session = MagicMock()
    session.get.return_value.raise_for_status.return_value = None
    session.get.return_value.json.return_value = "not a list or dict"

    df = extractor._fetch_corp_actions_api(session, date(2026, 1, 1), date(2026, 1, 31))

    assert df is None


# ── _normalize_corp_actions_columns ─────────────────────────────────────────


def test_normalize_corp_actions_columns_maps_api_field_names(extractor):
    df = pd.DataFrame(
        [
            {
                "symbol": "INFY",
                "subject": "Dividend",
                "exDate": "15-06-2026",
                "comp": "Infosys",
            }
        ]
    )
    out = extractor._normalize_corp_actions_columns(df)

    assert out.iloc[0]["SYMBOL"] == "INFY"
    assert out.iloc[0]["ACTION_TYPE_RAW"] == "Dividend"
    assert out.iloc[0]["EX_DATE"] == "15-06-2026"
    assert out.iloc[0]["COMPANY_NAME"] == "Infosys"


def test_normalize_corp_actions_columns_maps_playwright_scrape_headers(extractor):
    df = pd.DataFrame([{"Symbol": "INFY", "Purpose": "Bonus", "Ex Date": "15-06-2026"}])
    out = extractor._normalize_corp_actions_columns(df)

    assert out.iloc[0]["SYMBOL"] == "INFY"
    assert out.iloc[0]["ACTION_TYPE_RAW"] == "Bonus"
    assert out.iloc[0]["EX_DATE"] == "15-06-2026"


def test_normalize_corp_actions_columns_does_not_mutate_semantics_on_unknown_columns(
    extractor,
):
    df = pd.DataFrame([{"symbol": "INFY", "someUnknownField": "x"}])
    out = extractor._normalize_corp_actions_columns(df)
    assert "SOMEUNKNOWNFIELD" in out.columns


# ── _validate_corp_actions ──────────────────────────────────────────────────


def test_validate_corp_actions_happy_path_does_not_raise(extractor):
    df = pd.DataFrame(
        [{"SYMBOL": "INFY", "EX_DATE": "15-06-2026", "ACTION_TYPE_RAW": "Dividend"}]
    )
    extractor._validate_corp_actions(df)  # should not raise


def test_validate_corp_actions_missing_required_columns_raises(extractor):
    df = pd.DataFrame([{"SYMBOL": "INFY"}])  # missing EX_DATE, ACTION_TYPE_RAW
    with pytest.raises(ValueError, match="missing required columns"):
        extractor._validate_corp_actions(df)


def test_validate_corp_actions_null_symbol_logs_warning_not_raise(extractor):
    df = pd.DataFrame(
        [
            {"SYMBOL": None, "EX_DATE": "15-06-2026", "ACTION_TYPE_RAW": "Dividend"},
            {"SYMBOL": "INFY", "EX_DATE": "15-06-2026", "ACTION_TYPE_RAW": "Dividend"},
        ]
    )
    extractor._validate_corp_actions(df)  # should not raise despite the null symbol
