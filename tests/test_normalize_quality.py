"""
Tests for pipelines/normalize/quality.py (QualityMetadata).

No prior test coverage — closes part of the NSE core normalize test gap
(session of 2026-08-14). Also serves as a regression test for the
empty-DataFrame bug found and fixed the same day while adding
map_to_fact_equity_eod(): add_quality_flags() used `df.loc[:, col] = scalar`
to add new columns, which raised `ValueError: cannot set a frame with no
defined index and a scalar` on a zero-row DataFrame in this pandas version.
Fixed by switching to plain column assignment.

All tests are pure — no I/O, no network calls.
"""

import pandas as pd
import pytest

from pipelines.normalize.quality import QualityMetadata


@pytest.fixture()
def qm():
    return QualityMetadata(source_file="test_source.csv")


# ── add_quality_flags: happy path ───────────────────────────────────────────


def test_add_quality_flags_clean_row_gets_full_confidence(qm):
    df = pd.DataFrame([{"SYMBOL": "INFY", "ISIN": "INE001A01036"}])
    out = qm.add_quality_flags(df)

    assert out.iloc[0]["_confidence_score"] == 1.0
    assert out.iloc[0]["_quality_issues"] == ""
    assert out.iloc[0]["_manual_review_required"] == False  # noqa: E712
    assert out.iloc[0]["_source_file"] == "test_source.csv"


def test_add_quality_flags_missing_symbol_penalized(qm):
    df = pd.DataFrame([{"SYMBOL": None, "ISIN": "INE001A01036"}])
    out = qm.add_quality_flags(df)

    assert "MISSING_SYMBOL" in out.iloc[0]["_quality_issues"]
    assert out.iloc[0]["_confidence_score"] == pytest.approx(0.6)  # 1.0 - 0.4


def test_add_quality_flags_multiple_issues_stack_penalties(qm):
    df = pd.DataFrame([{"SYMBOL": None, "ISIN": None}])
    out = qm.add_quality_flags(df)

    issues = out.iloc[0]["_quality_issues"]
    assert "MISSING_SYMBOL" in issues
    assert "MISSING_ISIN" in issues
    assert out.iloc[0]["_confidence_score"] == pytest.approx(1.0 - 0.4 - 0.15)


def test_add_quality_flags_manual_review_flag_below_threshold(qm):
    df = pd.DataFrame([{"SYMBOL": None, "ISIN": None}])  # score 0.45, < 0.7 threshold
    out = qm.add_quality_flags(df)

    assert out.iloc[0]["_manual_review_required"] == True  # noqa: E712


def test_add_quality_flags_unresolved_symbol_marker_picked_up(qm):
    df = pd.DataFrame([{"SYMBOL": "INFY", "_unresolved_symbol": True}])
    out = qm.add_quality_flags(df)

    assert "UNRESOLVED_SYMBOL" in out.iloc[0]["_quality_issues"]


def test_add_quality_flags_unknown_action_type_flagged(qm):
    """
    Checks "action_code" — the column both RawToCanonicalMapper and
    BSERawToCanonicalMapper actually emit. Previously checked "ACTION_TYPE",
    a column neither mapper ever produced, so this flag never fired in
    production; fixed 2026-08-14 alongside adding this test.
    """
    df = pd.DataFrame([{"SYMBOL": "INFY", "action_code": "UNKNOWN"}])
    out = qm.add_quality_flags(df)

    assert "UNKNOWN_ACTION_TYPE" in out.iloc[0]["_quality_issues"]


# ── edge cases ───────────────────────────────────────────────────────────────


def test_add_quality_flags_empty_dataframe_does_not_raise(qm):
    df = pd.DataFrame(columns=["SYMBOL", "ISIN"])
    out = qm.add_quality_flags(df)

    assert out.empty
    for col in [
        "_source_file",
        "_extracted_date",
        "_quality_issues",
        "_confidence_score",
        "_manual_review_required",
    ]:
        assert col in out.columns


def test_add_quality_flags_all_null_column_all_rows_flagged(qm):
    df = pd.DataFrame({"SYMBOL": [None, None, None]})
    out = qm.add_quality_flags(df)

    assert (out["_quality_issues"].str.contains("MISSING_SYMBOL")).all()


def test_add_quality_flags_does_not_mutate_input(qm):
    df = pd.DataFrame([{"SYMBOL": "INFY", "ISIN": "INE001A01036"}])
    df_before = df.copy()

    qm.add_quality_flags(df)

    pd.testing.assert_frame_equal(df, df_before)


# ── score_to_flag ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "score,expected",
    [
        (1.0, "HIGH"),
        (0.9, "HIGH"),
        (0.89, "MEDIUM"),
        (0.7, "MEDIUM"),
        (0.69, "LOW"),
        (0.4, "LOW"),
        (0.39, "UNRESOLVED"),
        (0.0, "UNRESOLVED"),
    ],
)
def test_score_to_flag_thresholds(score, expected):
    assert QualityMetadata.score_to_flag(score) == expected


# ── flag_unresolved_symbols ──────────────────────────────────────────────────


def test_flag_unresolved_symbols_sets_marker_column():
    df = pd.DataFrame([{"SYMBOL": "A"}, {"SYMBOL": "B"}])
    mask = pd.Series([True, False])

    out = QualityMetadata.flag_unresolved_symbols(df, mask)

    assert out.iloc[0]["_unresolved_symbol"] == True  # noqa: E712
    assert out.iloc[1]["_unresolved_symbol"] == False  # noqa: E712


def test_flag_unresolved_symbols_does_not_mutate_input():
    df = pd.DataFrame([{"SYMBOL": "A"}])
    df_before = df.copy()
    mask = pd.Series([True])

    QualityMetadata.flag_unresolved_symbols(df, mask)

    pd.testing.assert_frame_equal(df, df_before)


# ── determinism ───────────────────────────────────────────────────────────────


def test_add_quality_flags_deterministic(qm):
    df = pd.DataFrame([{"SYMBOL": None, "ISIN": "INE001A01036"}])
    first = qm.add_quality_flags(df)
    second = qm.add_quality_flags(df)
    pd.testing.assert_frame_equal(first, second)
