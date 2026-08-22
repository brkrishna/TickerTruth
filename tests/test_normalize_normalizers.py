"""
Tests for pipelines/normalize/normalizers.py (FieldNormalizer).

Pure static field-level normalizers with no prior test coverage — part of
closing the NSE core normalize test gap (session of 2026-08-14, following
the lineage/adjustments coverage added earlier the same day).

Per pipelines/normalize/CLAUDE.md's testing rules, each public function
gets at least a happy-path, an edge-case, and an invalid-input test.

All tests are pure — no I/O, no network calls.
"""

from datetime import date

import pytest

from pipelines.normalize.normalizers import FieldNormalizer as FN


# ── normalize_ticker ─────────────────────────────────────────────────────────


def test_normalize_ticker_strips_series_suffix():
    assert FN.normalize_ticker("INFY-EQ") == "INFY"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("infy-eq", "INFY"),
        ("  TCS-BE  ", "TCS"),
        ("RELIANCE", "RELIANCE"),
        ("SBIN-N1", "SBIN"),
    ],
)
def test_normalize_ticker_variants(raw, expected):
    assert FN.normalize_ticker(raw) == expected


@pytest.mark.parametrize("bad", [None, "", "   ", 123, 12.5])
def test_normalize_ticker_invalid_input_returns_empty_string(bad):
    assert FN.normalize_ticker(bad) == ""


# ── normalize_company_name ───────────────────────────────────────────────────


def test_normalize_company_name_expands_legal_suffixes():
    assert (
        FN.normalize_company_name("Acme Industries Ltd.") == "ACME INDUSTRIES LIMITED"
    )


def test_normalize_company_name_replaces_ampersand():
    assert FN.normalize_company_name("Tata & Sons") == "TATA AND SONS"


def test_normalize_company_name_collapses_whitespace():
    assert (
        FN.normalize_company_name("Acme   Industries    Ltd")
        == "ACME INDUSTRIES LIMITED"
    )


def test_normalize_company_name_strips_non_ascii():
    # curly quote / accented char should be dropped, not raise
    result = FN.normalize_company_name("Café Industries Pvt Ltd")
    assert "CAF" in result
    assert "PRIVATE" in result
    assert "LIMITED" in result


@pytest.mark.parametrize("bad", [None, "", "   ", 42])
def test_normalize_company_name_invalid_input_returns_empty_string(bad):
    assert FN.normalize_company_name(bad) == ""


# ── normalize_date ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("28-05-2024", date(2024, 5, 28)),
        ("28/05/2024", date(2024, 5, 28)),
        ("2024-05-28", date(2024, 5, 28)),
        ("28-May-2024", date(2024, 5, 28)),
        ("28 May 2024", date(2024, 5, 28)),
    ],
)
def test_normalize_date_known_formats(raw, expected):
    assert FN.normalize_date(raw) == expected


@pytest.mark.parametrize(
    "bad", ["", "not-a-date", "NA", "N/A", "NULL", "-", None, 12345]
)
def test_normalize_date_invalid_or_missing_returns_none(bad):
    assert FN.normalize_date(bad) is None


# ── normalize_action_type ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Dividend", "DIVIDEND"),
        ("Bonus Issue", "BONUS"),
        ("Stock Split", "SPLIT"),
        ("Rights Issue", "RIGHTS"),
        ("Merger/Amalgamation", "MERGER"),
        ("Demerger", "DEMERGER"),
        ("Voluntary Delisting", "DELISTING"),
    ],
)
def test_normalize_action_type_known_values(raw, expected):
    assert FN.normalize_action_type(raw) == expected


def test_normalize_action_type_partial_match():
    # "Interim Dividend - Rs 5.00" isn't an exact key but contains "dividend"
    assert FN.normalize_action_type("Interim Dividend - Rs 5.00") == "DIVIDEND"


def test_normalize_action_type_scheme_of_arrangement_bonus_ncrps_is_merger():
    # A scheme of arrangement issuing preference shares ("Ncrps") is not a
    # common-equity bonus even though the raw text contains "bonus" — it
    # must not be classified as BONUS (would corrupt adjustment factors).
    assert (
        FN.normalize_action_type("Scheme Of Arrangement - Bonus Ncrps 4:1") == "MERGER"
    )


@pytest.mark.parametrize("bad", [None, "", "Something Completely Unrelated"])
def test_normalize_action_type_unknown_returns_unknown(bad):
    assert FN.normalize_action_type(bad) == "UNKNOWN"


# ── extract_bonus_adjustment_factor ──────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Bonus 1:1", 0.5),
        ("Bonus 1:2", 2 / 3),
        ("Bonus 2:1", 1 / 3),
        ("Bonus 1:3", 0.75),
        ("Bonus 10:1", 1 / 11),
    ],
)
def test_extract_bonus_adjustment_factor_known_ratios(raw, expected):
    assert FN.extract_bonus_adjustment_factor(raw) == pytest.approx(expected)


@pytest.mark.parametrize("bad", [None, "", "Dividend - Rs 5 Per Share", "Bonus"])
def test_extract_bonus_adjustment_factor_unparseable_returns_none(bad):
    assert FN.extract_bonus_adjustment_factor(bad) is None


# ── extract_split_adjustment_factor ──────────────────────────────────────────


def test_extract_split_adjustment_factor_face_value_split():
    text = (
        "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share"
    )
    assert FN.extract_split_adjustment_factor(text) == pytest.approx(0.2)


def test_extract_split_adjustment_factor_handles_re_one():
    text = (
        "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share"
    )
    assert FN.extract_split_adjustment_factor(text) == pytest.approx(0.1)


@pytest.mark.parametrize("bad", [None, "", "Bonus 1:1"])
def test_extract_split_adjustment_factor_unparseable_returns_none(bad):
    assert FN.extract_split_adjustment_factor(bad) is None


# ── normalize_numeric ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("5.00", 5.0),
        ("₹5.00", 5.0),
        ("Rs.5.00", 5.0),
        ("INR 5", 5.0),
        ("1,00,000", 100000.0),
        ("1:2", 0.5),
        ("10%", 0.1),
        (5, 5.0),
        (5.5, 5.5),
    ],
)
def test_normalize_numeric_valid_formats(raw, expected):
    assert FN.normalize_numeric(raw) == pytest.approx(expected)


@pytest.mark.parametrize(
    "bad", [None, "", "N/A", "NA", "NULL", "-", "not a number", [1, 2]]
)
def test_normalize_numeric_invalid_returns_none(bad):
    assert FN.normalize_numeric(bad) is None


def test_normalize_numeric_ratio_zero_denominator_returns_none():
    assert FN.normalize_numeric("1:0") is None


# ── determinism (all functions are pure statics) ────────────────────────────


def test_field_normalizer_functions_are_deterministic():
    assert FN.normalize_ticker("INFY-EQ") == FN.normalize_ticker("INFY-EQ")
    assert FN.normalize_company_name("Acme Ltd") == FN.normalize_company_name(
        "Acme Ltd"
    )
    assert FN.normalize_date("28-05-2024") == FN.normalize_date("28-05-2024")
    assert FN.normalize_action_type("Bonus") == FN.normalize_action_type("Bonus")
    assert FN.normalize_numeric("1:2") == FN.normalize_numeric("1:2")
