"""
Tests for pipelines/extract/extractor.py — consolidate_to_staging(),
_consolidate_source(), _write_quality_report(), _quality_warnings().
Part of closing the general extractor coverage gap.

Per pipelines/extract/CLAUDE.md's testing rules: "Test that
consolidate_to_staging() is idempotent (re-run does not duplicate rows)."

Uses real tmp_path directories for raw/staging (file I/O is this module's
whole job), but no network calls.
"""

import json

import pandas as pd
import pytest

from pipelines.extract.extractor import RawDataExtractor


@pytest.fixture()
def extractor(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    return RawDataExtractor(output_dir=raw_dir)


def _write_symbols_csv(raw_dir, filename, rows):
    df = pd.DataFrame(rows)
    df.to_csv(raw_dir / filename, index=False)


# ── consolidate_to_staging: happy path ──────────────────────────────────────


def test_consolidate_to_staging_merges_and_dedupes_symbols(extractor, tmp_path):
    staging = tmp_path / "staging"
    _write_symbols_csv(
        extractor.output_dir,
        "nse_symbols_2026-01-01.csv",
        [{"SYMBOL": "INFY", "LISTING_DATE": "1993-05-28"}],
    )
    _write_symbols_csv(
        extractor.output_dir,
        "nse_symbols_2026-01-02.csv",
        [
            {"SYMBOL": "INFY", "LISTING_DATE": "1993-05-28"},  # duplicate key
            {"SYMBOL": "TCS", "LISTING_DATE": "2004-08-25"},
        ],
    )

    report = extractor.consolidate_to_staging(staging_dir=staging)

    out_file = staging / "nse_symbols_consolidated.csv"
    assert out_file.exists()
    out_df = pd.read_csv(out_file)
    assert len(out_df) == 2  # INFY deduped, TCS added
    assert report["symbols"]["files_found"] == 2
    assert report["symbols"]["rows_before_dedup"] == 3
    assert report["symbols"]["rows_after_dedup"] == 2


def test_consolidate_to_staging_writes_quality_report_json(extractor, tmp_path):
    from datetime import date

    staging = tmp_path / "staging"
    _write_symbols_csv(
        extractor.output_dir, "nse_symbols_2026-01-01.csv", [{"SYMBOL": "INFY"}]
    )

    run_date = date(2026, 6, 15)
    extractor.consolidate_to_staging(staging_dir=staging, run_date=run_date)

    report_path = staging / "quality_report_2026-06-15.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["generated_on"] == "2026-06-15"
    assert "sources" in data
    assert "warnings" in data


def test_consolidate_to_staging_is_idempotent(extractor, tmp_path):
    """Re-running consolidation on the same raw files does not duplicate rows."""
    staging = tmp_path / "staging"
    _write_symbols_csv(
        extractor.output_dir,
        "nse_symbols_2026-01-01.csv",
        [{"SYMBOL": "INFY", "LISTING_DATE": "1993-05-28"}],
    )

    extractor.consolidate_to_staging(staging_dir=staging)
    first = pd.read_csv(staging / "nse_symbols_consolidated.csv")

    extractor.consolidate_to_staging(staging_dir=staging)
    second = pd.read_csv(staging / "nse_symbols_consolidated.csv")

    assert len(first) == len(second) == 1


def test_consolidate_to_staging_no_raw_files_returns_zero_counts(extractor, tmp_path):
    staging = tmp_path / "staging"
    report = extractor.consolidate_to_staging(staging_dir=staging)

    assert report["symbols"]["files_found"] == 0
    assert report["symbols"]["rows_after_dedup"] == 0
    assert not (staging / "nse_symbols_consolidated.csv").exists()


# ── _consolidate_source ──────────────────────────────────────────────────────


def test_consolidate_source_skips_unreadable_file_and_continues(extractor, tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_symbols_csv(
        extractor.output_dir, "nse_symbols_2026-01-01.csv", [{"SYMBOL": "INFY"}]
    )
    # A corrupt file matching the same glob pattern
    (extractor.output_dir / "nse_symbols_2026-01-02.csv").write_bytes(
        b"\xff\xfe\x00garbage"
    )

    result = extractor._consolidate_source(
        pattern="nse_symbols_*.csv",
        out_file=staging / "nse_symbols_consolidated.csv",
        dedup_cols=["SYMBOL"],
        date_col="LISTING_DATE",
        label="NSE symbols",
    )

    assert result["files_found"] == 2
    # the corrupt file was skipped; the valid one still made it through
    assert result["rows_after_dedup"] >= 1


def test_consolidate_source_computes_date_range(extractor, tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_symbols_csv(
        extractor.output_dir,
        "nse_symbols_2026-01-01.csv",
        [
            {"SYMBOL": "A", "LISTING_DATE": "2020-01-01"},
            {"SYMBOL": "B", "LISTING_DATE": "2022-06-15"},
        ],
    )

    result = extractor._consolidate_source(
        pattern="nse_symbols_*.csv",
        out_file=staging / "out.csv",
        dedup_cols=["SYMBOL"],
        date_col="LISTING_DATE",
        label="NSE symbols",
    )

    assert result["date_range"] == ("2020-01-01", "2022-06-15")


def test_consolidate_source_missing_dedup_columns_skips_dedup_gracefully(
    extractor, tmp_path
):
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_symbols_csv(
        extractor.output_dir,
        "nse_symbols_2026-01-01.csv",
        [{"SYMBOL": "A"}, {"SYMBOL": "A"}],  # dedup col "MISSING_COL" isn't present
    )

    result = extractor._consolidate_source(
        pattern="nse_symbols_*.csv",
        out_file=staging / "out.csv",
        dedup_cols=["MISSING_COL"],
        date_col="LISTING_DATE",
        label="NSE symbols",
    )

    # no dedup possible -> both rows retained
    assert result["rows_after_dedup"] == 2


# ── _quality_warnings ─────────────────────────────────────────────────────────


def test_quality_warnings_flags_missing_files():
    report = {
        "symbols": {"files_found": 0, "rows_before_dedup": 0, "rows_after_dedup": 0}
    }
    warnings = RawDataExtractor._quality_warnings(report)
    assert any("no raw files found" in w for w in warnings)


def test_quality_warnings_flags_high_duplicate_ratio():
    report = {
        "actions": {"files_found": 2, "rows_before_dedup": 100, "rows_after_dedup": 80}
    }
    warnings = RawDataExtractor._quality_warnings(report)
    assert any("duplicate rows removed" in w for w in warnings)


def test_quality_warnings_flags_zero_rows_after_dedup():
    report = {
        "actions": {"files_found": 1, "rows_before_dedup": 5, "rows_after_dedup": 0}
    }
    warnings = RawDataExtractor._quality_warnings(report)
    assert any("0 rows after dedup" in w for w in warnings)


def test_quality_warnings_clean_report_produces_no_warnings():
    report = {
        "symbols": {"files_found": 1, "rows_before_dedup": 100, "rows_after_dedup": 100}
    }
    warnings = RawDataExtractor._quality_warnings(report)
    assert warnings == []
