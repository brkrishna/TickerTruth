"""
Tests for RawDataExtractor._stale_corp_actions_fallback() and the stale-cache
path inside fetch_nse_corporate_actions().

All tests are pure — no live network calls.
"""

import pandas as pd
import pytest

from pipelines.extract.extractor import RawDataExtractor


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def extractor(tmp_path):
    return RawDataExtractor(output_dir=tmp_path)


def _write_actions_csv(path, rows=1):
    """Write a minimal nse_actions CSV to path."""
    df = pd.DataFrame({
        "SYMBOL": ["INFY"] * rows,
        "EX_DATE": ["2026-01-15"] * rows,
        "ACTION_TYPE_RAW": ["DIVIDEND"] * rows,
    })
    df.to_csv(path, index=False)
    return df


# ── _stale_corp_actions_fallback ──────────────────────────────────────────────

def test_stale_fallback_no_files_returns_none(extractor):
    assert extractor._stale_corp_actions_fallback() is None


def test_stale_fallback_returns_most_recent_file(extractor, tmp_path):
    older = tmp_path / "nse_actions_2026-01-01_2026-01-31.csv"
    newer = tmp_path / "nse_actions_2026-04-01_2026-04-30.csv"
    _write_actions_csv(older)
    _write_actions_csv(newer, rows=3)

    result = extractor._stale_corp_actions_fallback()
    assert result is not None
    assert len(result) == 3, "should return content of newer file"


def test_stale_fallback_skips_empty_files(extractor, tmp_path):
    empty = tmp_path / "nse_actions_2026-05-01_2026-05-31.csv"
    empty.write_text("")  # zero bytes

    valid = tmp_path / "nse_actions_2026-04-01_2026-04-30.csv"
    _write_actions_csv(valid, rows=2)

    result = extractor._stale_corp_actions_fallback()
    assert result is not None
    assert len(result) == 2, "should skip empty file and use the valid one"


def test_stale_fallback_returns_none_when_only_empty_files(extractor, tmp_path):
    empty = tmp_path / "nse_actions_2026-05-01_2026-05-31.csv"
    empty.write_text("")

    assert extractor._stale_corp_actions_fallback() is None


def test_stale_fallback_returns_none_on_corrupt_file(extractor, tmp_path, monkeypatch):
    bad = tmp_path / "nse_actions_2026-04-01_2026-04-30.csv"
    bad.write_text("not,valid\ncsv\x00data")

    monkeypatch.setattr(pd, "read_csv", lambda *a, **kw: (_ for _ in ()).throw(ValueError("bad")))

    result = extractor._stale_corp_actions_fallback()
    assert result is None


# ── fetch_nse_corporate_actions stale-cache integration ───────────────────────

def test_fetch_uses_stale_cache_when_all_live_methods_fail(extractor, tmp_path, monkeypatch):
    """When API and Playwright both fail, the stale file is returned."""
    stale = tmp_path / "nse_actions_2026-03-01_2026-03-31.csv"
    _write_actions_csv(stale, rows=5)

    monkeypatch.setattr(extractor, "_get_session", lambda: object())
    monkeypatch.setattr(extractor, "_fetch_corp_actions_api", lambda *a, **kw: None)
    monkeypatch.setattr(extractor, "_fetch_corp_actions_playwright", lambda *a, **kw: None)

    from datetime import date
    result = extractor.fetch_nse_corporate_actions(
        from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
    )
    assert result is not None
    assert len(result) == 5


def test_fetch_raises_when_all_methods_fail_and_no_stale(extractor, monkeypatch):
    """RuntimeError when API, Playwright, and stale cache all fail."""
    monkeypatch.setattr(extractor, "_get_session", lambda: object())
    monkeypatch.setattr(extractor, "_fetch_corp_actions_api", lambda *a, **kw: None)
    monkeypatch.setattr(extractor, "_fetch_corp_actions_playwright", lambda *a, **kw: None)

    from datetime import date
    with pytest.raises(RuntimeError, match="stale cache"):
        extractor.fetch_nse_corporate_actions(
            from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
        )
