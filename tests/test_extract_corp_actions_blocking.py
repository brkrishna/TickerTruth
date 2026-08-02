"""
Tests for Akamai-edge-block detection in RawDataExtractor:

- _get_session() sets _homepage_blocked on an HTTP 403 from the NSE homepage,
  and does NOT set it for other failure types (timeouts, 5xx, etc).
- fetch_nse_corporate_actions() skips the Playwright fallback when the block
  is already known, instead of burning time on a fallback that would hit the
  same blocked domain and fail identically.

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


# ── _get_session() block detection ──────────────────────────────────────────


def test_get_session_sets_blocked_flag_on_403(extractor):
    with patch("requests.Session.get", side_effect=_http_error(403)):
        extractor._get_session()
    assert extractor._homepage_blocked is True


def test_get_session_leaves_flag_false_on_timeout(extractor):
    with patch(
        "requests.Session.get",
        side_effect=requests.exceptions.Timeout("read timed out"),
    ):
        extractor._get_session()
    assert extractor._homepage_blocked is False


def test_get_session_leaves_flag_false_on_success(extractor):
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.raise_for_status.return_value = None
    with patch("requests.Session.get", return_value=ok_resp):
        extractor._get_session()
    assert extractor._homepage_blocked is False


def test_get_session_leaves_flag_false_on_non_403_http_error(extractor):
    with patch("requests.Session.get", side_effect=_http_error(500)):
        extractor._get_session()
    assert extractor._homepage_blocked is False


# ── fetch_nse_corporate_actions() skip-Playwright-when-blocked ──────────────


def test_skips_playwright_when_homepage_blocked(extractor, monkeypatch):
    extractor._homepage_blocked = True
    monkeypatch.setattr(extractor, "_get_session", lambda: object())
    monkeypatch.setattr(extractor, "_fetch_corp_actions_api", lambda *a, **kw: None)
    monkeypatch.setattr(extractor, "_stale_corp_actions_fallback", lambda: None)

    playwright_mock = MagicMock()
    monkeypatch.setattr(extractor, "_fetch_corp_actions_playwright", playwright_mock)

    with pytest.raises(RuntimeError, match="Akamai"):
        extractor.fetch_nse_corporate_actions(
            from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
        )

    playwright_mock.assert_not_called()


def test_tries_playwright_when_not_blocked(extractor, monkeypatch):
    extractor._homepage_blocked = False
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


def test_uses_stale_cache_when_blocked_and_available(extractor, monkeypatch):
    import pandas as pd

    extractor._homepage_blocked = True
    monkeypatch.setattr(extractor, "_get_session", lambda: object())
    monkeypatch.setattr(extractor, "_fetch_corp_actions_api", lambda *a, **kw: None)
    stale = pd.DataFrame({"SYMBOL": ["INFY"]})
    monkeypatch.setattr(extractor, "_stale_corp_actions_fallback", lambda: stale)

    playwright_mock = MagicMock()
    monkeypatch.setattr(extractor, "_fetch_corp_actions_playwright", playwright_mock)

    result = extractor.fetch_nse_corporate_actions(
        from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
    )

    assert result is stale
    playwright_mock.assert_not_called()
