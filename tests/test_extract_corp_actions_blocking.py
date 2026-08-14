"""
Tests for RawDataExtractor's handling of NSE's homepage HTTP 403.

Confirmed 2026-08-14: the NSE homepage returns 403, but its Set-Cookie
header (AKA_A2) still lands in the session and is sufficient to
authenticate the JSON API. A homepage 403 must NOT be treated as a hard
block — _get_session() should log it and continue, and
fetch_nse_corporate_actions() should still attempt the Playwright
fallback (and then stale cache) on a JSON API failure exactly as it
would for any other failure reason.

All tests are pure — no live network calls.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from pipelines.extract.extractor import RawDataExtractor


@pytest.fixture()
def extractor(tmp_path):
    return RawDataExtractor(output_dir=tmp_path)


def _http_error(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    return requests.HTTPError(response=resp)


# ── _get_session() does not treat 403 as fatal ──────────────────────────────


def test_get_session_returns_usable_session_on_403(extractor):
    with patch("requests.Session.get", side_effect=_http_error(403)):
        session = extractor._get_session()
    assert session is not None
    # A second call reuses the cached session rather than re-raising.
    assert extractor._get_session() is session


def test_get_session_returns_usable_session_on_timeout(extractor):
    with patch(
        "requests.Session.get",
        side_effect=requests.exceptions.Timeout("read timed out"),
    ):
        session = extractor._get_session()
    assert session is not None


def test_get_session_returns_usable_session_on_success(extractor):
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.raise_for_status.return_value = None
    with patch("requests.Session.get", return_value=ok_resp):
        session = extractor._get_session()
    assert session is not None


def test_get_session_returns_usable_session_on_non_403_http_error(extractor):
    with patch("requests.Session.get", side_effect=_http_error(500)):
        session = extractor._get_session()
    assert session is not None


# ── fetch_nse_corporate_actions() always tries Playwright on API failure ────


def test_tries_playwright_when_api_fails(extractor, monkeypatch):
    monkeypatch.setattr(extractor, "_get_session", lambda: object())
    monkeypatch.setattr(extractor, "_fetch_corp_actions_api", lambda *a, **kw: None)
    monkeypatch.setattr(extractor, "_stale_corp_actions_fallback", lambda: None)

    playwright_mock = MagicMock(return_value=None)
    monkeypatch.setattr(extractor, "_fetch_corp_actions_playwright", playwright_mock)

    with pytest.raises(RuntimeError):
        extractor.fetch_nse_corporate_actions(
            from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
        )

    playwright_mock.assert_called_once()


def test_uses_stale_cache_when_api_and_playwright_fail(extractor, monkeypatch):
    import pandas as pd

    monkeypatch.setattr(extractor, "_get_session", lambda: object())
    monkeypatch.setattr(extractor, "_fetch_corp_actions_api", lambda *a, **kw: None)
    stale = pd.DataFrame({"SYMBOL": ["INFY"]})
    monkeypatch.setattr(extractor, "_stale_corp_actions_fallback", lambda: stale)

    playwright_mock = MagicMock(return_value=None)
    monkeypatch.setattr(extractor, "_fetch_corp_actions_playwright", playwright_mock)

    result = extractor.fetch_nse_corporate_actions(
        from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
    )

    assert result is stale
    playwright_mock.assert_called_once()
