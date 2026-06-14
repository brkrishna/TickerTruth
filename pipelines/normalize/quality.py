"""
Quality metadata tagging for normalized DataFrames.

Adds five provenance/quality columns to any normalized DataFrame so that
downstream consumers can filter by confidence and trace data back to source.
"""

from datetime import date

import pandas as pd


# Columns whose presence and null rate are checked automatically
_CRITICAL_COLUMNS: dict[str, str] = {
    "SYMBOL": "MISSING_SYMBOL",
    "ISIN": "MISSING_ISIN",
    "LISTING_DATE": "MISSING_LISTING_DATE",
    "EX_DATE": "MISSING_EX_DATE",
    "ACTION_TYPE_RAW": "MISSING_ACTION_TYPE",
}

# Confidence penalty per quality issue (deducted from 1.0)
_ISSUE_PENALTY: dict[str, float] = {
    "MISSING_SYMBOL": 0.4,  # hard — symbol is the primary key
    "MISSING_ISIN": 0.15,
    "MISSING_LISTING_DATE": 0.1,
    "MISSING_EX_DATE": 0.2,  # hard for corporate actions
    "MISSING_ACTION_TYPE": 0.2,
    "UNKNOWN_ACTION_TYPE": 0.15,
    "INVALID_DATE": 0.1,
    "UNRESOLVED_SYMBOL": 0.3,  # symbol not in security master
    "DUPLICATE_KEY": 0.1,
}

# Score below this threshold triggers manual_review_required = True
_MANUAL_REVIEW_THRESHOLD = 0.7


class QualityMetadata:
    """
    Appends quality/provenance columns to a normalized DataFrame.

    Usage:
        qm = QualityMetadata(source_file="nse_symbols_2026-05-31.csv")
        df = qm.add_quality_flags(df)
        # df now has: _source_file, _extracted_date, _quality_issues,
        #             _confidence_score, _manual_review_required
    """

    def __init__(self, source_file: str = "", extracted_date: date | None = None):
        self.source_file = source_file
        self.extracted_date = (extracted_date or date.today()).isoformat()

    def add_quality_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add five quality/provenance columns to df (in-place copy returned).

        Columns added:
            _source_file           — filename the data came from
            _extracted_date        — ISO date when extraction ran
            _quality_issues        — comma-separated issue codes per row
            _confidence_score      — float [0.0, 1.0]; 1.0 = clean
            _manual_review_required — True if score < 0.7

        Existing quality columns are overwritten if present.
        """
        df = df.copy()

        df.loc[:, "_source_file"] = self.source_file
        df.loc[:, "_extracted_date"] = self.extracted_date

        issues_series = df.apply(self._detect_issues, axis=1)
        df.loc[:, "_quality_issues"] = issues_series.apply(
            lambda codes: ",".join(codes) if codes else ""
        )
        df.loc[:, "_confidence_score"] = issues_series.apply(self._score)
        df.loc[:, "_manual_review_required"] = (
            df["_confidence_score"] < _MANUAL_REVIEW_THRESHOLD
        )

        return df

    @staticmethod
    def _detect_issues(row: pd.Series) -> list[str]:
        """
        Inspect a single row and return a list of quality issue codes.

        Checks only columns that are actually present in the row — so the
        same method works for symbols, bhavcopy, and corporate action rows.
        """
        issues: list[str] = []

        for col, issue_code in _CRITICAL_COLUMNS.items():
            if col in row.index:
                val = row[col]
                if pd.isna(val) or str(val).strip() in ("", "N/A", "NA", "NULL"):
                    issues.append(issue_code)

        # Flag rows where action type normalization returned UNKNOWN
        if "ACTION_TYPE" in row.index:
            if str(row["ACTION_TYPE"]).strip().upper() == "UNKNOWN":
                issues.append("UNKNOWN_ACTION_TYPE")

        # Flag unresolved symbol (set by RawToCanonicalMapper when JOIN fails)
        if row.get("_unresolved_symbol", False):
            issues.append("UNRESOLVED_SYMBOL")

        return issues

    @staticmethod
    def _score(issue_codes: list[str]) -> float:
        """Compute confidence score by subtracting per-issue penalties from 1.0."""
        score = 1.0
        for code in issue_codes:
            score -= _ISSUE_PENALTY.get(code, 0.05)
        return round(max(0.0, score), 4)

    @staticmethod
    def score_to_flag(score: float) -> str:
        """Map a numeric confidence score to a categorical confidence flag.

        HIGH       >= 0.9  official source, all critical fields present
        MEDIUM     >= 0.7  scraped or partially complete
        LOW        >= 0.4  estimated or ambiguous source
        UNRESOLVED  < 0.4  conflicting or critically incomplete; do not use in production
        """
        if score >= 0.9:
            return "HIGH"
        elif score >= 0.7:
            return "MEDIUM"
        elif score >= 0.4:
            return "LOW"
        else:
            return "UNRESOLVED"

    @classmethod
    def flag_unresolved_symbols(
        cls, df: pd.DataFrame, unresolved_mask: pd.Series
    ) -> pd.DataFrame:
        """
        Mark rows where the symbol could not be resolved to a security_id.

        Sets a temporary _unresolved_symbol column that add_quality_flags()
        picks up when computing issues and confidence scores.

        Args:
            df:               DataFrame to update
            unresolved_mask:  Boolean Series (True = unresolved)
        """
        df = df.copy()
        df["_unresolved_symbol"] = unresolved_mask
        return df
