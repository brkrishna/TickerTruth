"""
Tests for:
- RawDataExtractor._stale_corp_actions_fallback() and the stale-cache path
  inside fetch_nse_corporate_actions().
- RawDataExtractor._check_bhavcopy_staleness() and the run_date parameter
  on consolidate_to_staging() (BUG-5).

All tests are pure — no live network calls.
"""

import pandas as pd
import pytest
from datetime import date

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

    with pytest.raises(RuntimeError, match="stale cache"):
        extractor.fetch_nse_corporate_actions(
            from_date=date(2026, 5, 1), to_date=date(2026, 5, 31)
        )


# ── _check_bhavcopy_staleness (BUG-5) ────────────────────────────────────────

def _write_bhavcopy_csv(path):
    """Write a minimal bhavcopy CSV to path."""
    pd.DataFrame({
        "SYMBOL": ["INFY"],
        "OPEN": [1500.0],
        "HIGH": [1510.0],
        "LOW": [1495.0],
        "CLOSE": [1505.0],
        "TIMESTAMP": [path.stem.replace("bhavcopy_", "")],
    }).to_csv(path, index=False)


def test_staleness_no_files_is_silent(extractor, caplog):
    """No warning when there are no bhavcopy files at all."""
    import logging
    with caplog.at_level(logging.WARNING):
        extractor._check_bhavcopy_staleness(date(2026, 6, 1))
    assert "stale" not in caplog.text.lower()


def test_staleness_fresh_file_is_silent(extractor, tmp_path, caplog):
    """No warning when the most recent bhavcopy is within the threshold."""
    _write_bhavcopy_csv(tmp_path / "bhavcopy_2026-05-30.csv")
    import logging
    with caplog.at_level(logging.WARNING):
        extractor._check_bhavcopy_staleness(date(2026, 6, 1))  # 2 days gap — under threshold
    assert "stale" not in caplog.text.lower()


def test_staleness_old_file_warns(extractor, tmp_path, caplog):
    """Warning logged when the most recent bhavcopy is older than the threshold."""
    _write_bhavcopy_csv(tmp_path / "bhavcopy_2024-05-10.csv")
    import logging
    with caplog.at_level(logging.WARNING):
        extractor._check_bhavcopy_staleness(date(2026, 6, 1))
    assert "stale" in caplog.text.lower()
    assert "bhavcopy_2024-05-10.csv" in caplog.text


def test_staleness_uses_most_recent_file(extractor, tmp_path, caplog):
    """Only the newest bhavcopy file is checked, not older ones."""
    _write_bhavcopy_csv(tmp_path / "bhavcopy_2024-05-10.csv")  # very old
    _write_bhavcopy_csv(tmp_path / "bhavcopy_2026-05-29.csv")  # recent
    import logging
    with caplog.at_level(logging.WARNING):
        extractor._check_bhavcopy_staleness(date(2026, 6, 1))  # 3 days — under threshold
    assert "stale" not in caplog.text.lower()


def test_staleness_skips_empty_files(extractor, tmp_path, caplog):
    """Empty files are ignored; the next valid file is checked."""
    empty = tmp_path / "bhavcopy_2026-06-01.csv"
    empty.write_text("")  # zero bytes — excluded by size > 0 filter
    _write_bhavcopy_csv(tmp_path / "bhavcopy_2024-05-10.csv")
    import logging
    with caplog.at_level(logging.WARNING):
        extractor._check_bhavcopy_staleness(date(2026, 6, 1))
    assert "stale" in caplog.text.lower()


def test_staleness_malformed_filename_is_silent(extractor, tmp_path, caplog):
    """A bhavcopy file with an unparseable date in the name doesn't crash."""
    bad = tmp_path / "bhavcopy_UNKNOWN.csv"
    bad.write_text("col\nval")
    import logging
    with caplog.at_level(logging.WARNING):
        extractor._check_bhavcopy_staleness(date(2026, 6, 1))
    assert "error" not in caplog.text.lower()


# ── consolidate_to_staging run_date integration ───────────────────────────────

def test_consolidate_passes_run_date_to_staleness_check(extractor, tmp_path, monkeypatch, caplog):
    """consolidate_to_staging forwards run_date so staleness check uses the right date."""
    _write_bhavcopy_csv(tmp_path / "bhavcopy_2024-05-10.csv")

    # Stub out the other consolidation sources so we don't need real files
    monkeypatch.setattr(extractor, "_consolidate_source", lambda **kw: {
        "files_found": 0, "rows_before_dedup": 0, "rows_after_dedup": 0, "date_range": None
    })
    monkeypatch.setattr(extractor, "_write_quality_report", lambda *a, **kw: None)

    import logging
    with caplog.at_level(logging.WARNING):
        extractor.consolidate_to_staging(
            staging_dir=tmp_path / "staging",
            run_date=date(2026, 6, 1),
        )
    assert "stale" in caplog.text.lower()
