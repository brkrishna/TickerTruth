"""
Maps raw NSE staging DataFrames to canonical Dolt schema tables.

Depends on:
    FieldNormalizer  (normalizers.py) — field-level cleaning
    QualityMetadata  (quality.py)     — provenance / confidence tagging

Output DataFrames match the column names in dolt/schema.sql so they can
be written directly to data/curated/ and loaded into Dolt in Task 9.
"""

from pathlib import Path

import pandas as pd

from pipelines.normalize.normalizers import FieldNormalizer as FN
from pipelines.normalize.quality import QualityMetadata

DATA_CURATED = Path(__file__).parent.parent.parent / "data" / "curated"

# NSE exchange_id — hardcoded for MVP (single exchange)
NSE_EXCHANGE_ID = 1

# Canonical action codes that map to dim_corporate_action_type.action_code
# Used to look up action_type_id during fact table mapping
_KNOWN_ACTION_CODES = {
    "DIVIDEND",
    "BONUS",
    "SPLIT",
    "REVERSE_SPLIT",
    "RIGHTS",
    "PREFERENCE_DIVIDEND",
    "DIVIDEND_REINVESTMENT",
    "DELISTING",
    "RELISTING",
    "MERGER",
    "DEMERGER",
    "NAME_CHANGE",
    "CAPITAL_REDUCTION",
    "CAPITAL_INCREASE",
    "LISTING",
    "SPECIAL_DIVIDEND",
}


class RawToCanonicalMapper:
    """
    Maps raw staging DataFrames to canonical schema-aligned DataFrames.

    Typical call sequence:
        mapper = RawToCanonicalMapper(source_file="nse_symbols_consolidated.csv")
        dim_issuer   = mapper.map_to_dim_issuer(raw_symbols)
        dim_security = mapper.map_to_dim_security_master(raw_symbols, dim_issuer)
        fact_actions = mapper.map_to_fact_corporate_action_event(raw_actions, dim_security)
    """

    def __init__(self, source_file: str = ""):
        self._qm = QualityMetadata(source_file=source_file)

    # ── dim_issuer ────────────────────────────────────────────────────────────

    def map_to_dim_issuer(self, raw_symbols: pd.DataFrame) -> pd.DataFrame:
        """
        Build dim_issuer from raw symbols staging data.

        Extracts unique company names, normalises them, and assigns
        sequential surrogate issuer_ids starting from 1.

        Output columns (match dim_issuer in schema.sql):
            issuer_id, issuer_name, sector, market_cap_category, country

        Args:
            raw_symbols: consolidated symbols staging DataFrame. Expected
                         to have COMPANY_NAME and optionally SECTOR columns.

        Returns:
            dim_issuer DataFrame, one row per unique issuer.
        """
        name_col = self._find_col(raw_symbols, ["COMPANY_NAME", "NAME", "COMP"])
        sector_col = self._find_col(
            raw_symbols, ["SECTOR", "INDUSTRY", "INDUSTRY_NAME"]
        )

        if name_col is None:
            raise ValueError(
                "raw_symbols has no company name column. "
                f"Expected one of: COMPANY_NAME, NAME, COMP. Got: {list(raw_symbols.columns)}"
            )

        # Normalise names and deduplicate
        names = raw_symbols[name_col].dropna().unique()
        rows = []
        for name in names:
            norm = FN.normalize_company_name(name)
            if norm:
                rows.append({"_raw_name": name, "issuer_name": norm})

        df = pd.DataFrame(rows).drop_duplicates(subset=["issuer_name"])
        df = df.reset_index(drop=True)
        df["issuer_id"] = df.index + 1

        # Carry sector if available
        if sector_col:
            sector_map = (
                raw_symbols[[name_col, sector_col]]
                .dropna(subset=[name_col])
                .assign(
                    **{name_col: raw_symbols[name_col].apply(FN.normalize_company_name)}
                )
                .drop_duplicates(subset=[name_col])
                .set_index(name_col)[sector_col]
            )
            df["sector"] = df["issuer_name"].map(sector_map)
        else:
            df["sector"] = None

        df["market_cap_category"] = None
        df["country"] = "India"

        # Drop the working column
        df.drop(columns=["_raw_name"], inplace=True)

        return df[
            ["issuer_id", "issuer_name", "sector", "market_cap_category", "country"]
        ]

    # ── dim_security_master ───────────────────────────────────────────────────

    def map_to_dim_security_master(
        self,
        raw_symbols: pd.DataFrame,
        dim_issuer: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build dim_security_master from raw symbols + dim_issuer.

        Normalises ticker symbols, dates, and status flags. Joins with
        dim_issuer on normalised company name to resolve issuer_id.
        Rows where issuer_id cannot be resolved are flagged as quality issues.

        Output columns (match dim_security_master in schema.sql):
            security_id, nse_symbol, isin, company_name, issuer_id,
            exchange_id, listing_date, active_flag

        Args:
            raw_symbols: consolidated symbols staging DataFrame.
            dim_issuer:  output of map_to_dim_issuer().

        Returns:
            dim_security_master DataFrame, one row per unique symbol.
        """
        df = raw_symbols.copy()

        symbol_col = self._find_col(df, ["SYMBOL"])
        name_col = self._find_col(df, ["COMPANY_NAME", "NAME", "COMP"])
        isin_col = self._find_col(df, ["ISIN", "ISIN_NUMBER", "ISIN NUMBER"])
        date_col = self._find_col(
            df, ["LISTING_DATE", "DATE OF LISTING", "DATE_OF_LISTING"]
        )
        status_col = self._find_col(df, ["STATUS", "TRADING_STATUS", "TRADING STATUS"])

        if symbol_col is None:
            raise ValueError("raw_symbols missing SYMBOL column")

        # Normalise ticker
        df.loc[:, "nse_symbol"] = df[symbol_col].apply(FN.normalize_ticker)

        # Normalise company name and resolve issuer_id via join
        if name_col:
            df.loc[:, "_norm_name"] = df[name_col].apply(FN.normalize_company_name)
            df.loc[:, "company_name"] = df["_norm_name"]
        else:
            df.loc[:, "_norm_name"] = ""
            df.loc[:, "company_name"] = ""

        issuer_lookup = dim_issuer.set_index("issuer_name")["issuer_id"]
        df.loc[:, "issuer_id"] = df["_norm_name"].map(issuer_lookup)

        # Flag rows where issuer could not be resolved
        unresolved = df["issuer_id"].isna()
        if unresolved.any():
            df = QualityMetadata.flag_unresolved_symbols(df, unresolved)

        # Normalise ISIN
        df.loc[:, "isin"] = df[isin_col].str.strip().str.upper() if isin_col else None

        # Normalise listing_date
        df.loc[:, "listing_date"] = (
            df[date_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if date_col
            else None
        )

        # Derive active_flag from STATUS column
        df.loc[:, "active_flag"] = True
        if status_col:
            inactive = (
                df[status_col]
                .str.upper()
                .isin(["DELISTED", "SUSPENDED", "INACTIVE", "UNLISTED"])
            )
            df.loc[inactive, "active_flag"] = False

        df.loc[:, "exchange_id"] = NSE_EXCHANGE_ID

        # Deduplicate on normalised symbol (keep last — most recent status)
        df.drop_duplicates(subset=["nse_symbol"], keep="last", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.loc[:, "security_id"] = df.index + 1

        # Apply quality flags
        df = self._qm.add_quality_flags(df)

        # Drop working columns
        df.drop(columns=["_norm_name"], errors="ignore", inplace=True)
        df.drop(columns=["_unresolved_symbol"], errors="ignore", inplace=True)

        out_cols = [
            "security_id",
            "nse_symbol",
            "isin",
            "company_name",
            "issuer_id",
            "exchange_id",
            "listing_date",
            "active_flag",
            "_source_file",
            "_extracted_date",
            "_quality_issues",
            "_confidence_score",
            "_manual_review_required",
        ]
        return df[[c for c in out_cols if c in df.columns]]

    # ── fact_corporate_action_event ───────────────────────────────────────────

    def map_to_fact_corporate_action_event(
        self,
        raw_actions: pd.DataFrame,
        dim_security_master: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build fact_corporate_action_event from raw corporate actions + dim_security_master.

        Resolves security_id via symbol join. Normalises action types,
        dates, and numeric values. Rows with unresolvable symbols are
        retained but flagged as quality issues.

        Output columns (match fact_corporate_action_event in schema.sql):
            security_id, action_code, event_date, record_date, payment_date,
            old_value, new_value, adjustment_factor, confidence_score

        Note: action_type_id (FK to dim_corporate_action_type) is resolved
        by the Dolt loader in Task 9. This output uses action_code strings.

        Args:
            raw_actions:        consolidated corporate actions staging DataFrame.
            dim_security_master: output of map_to_dim_security_master().

        Returns:
            fact_corporate_action_event DataFrame.
        """
        df = raw_actions.copy()

        symbol_col = self._find_col(df, ["SYMBOL"])
        action_col = self._find_col(df, ["ACTION_TYPE_RAW", "SUBJECT", "PURPOSE"])
        exdate_col = self._find_col(df, ["EX_DATE", "EX DATE", "EXDATE"])
        recdate_col = self._find_col(df, ["RECORD_DATE", "RECORD DATE", "RECDATE"])
        paydate_col = self._find_col(df, ["PAYMENT_DATE", "PAYMENT DATE", "PAYDATE"])
        value_col = self._find_col(
            df, ["VALUE_OR_RATIO", "VALUE", "FACEVALUE", "FACE_VALUE"]
        )

        if symbol_col is None or action_col is None or exdate_col is None:
            raise ValueError(
                "raw_actions missing required columns. "
                f"Need SYMBOL, ACTION_TYPE_RAW, EX_DATE. Got: {list(df.columns)}"
            )

        # Normalise ticker and resolve security_id
        df.loc[:, "_norm_symbol"] = df[symbol_col].apply(FN.normalize_ticker)
        security_lookup = dim_security_master.set_index("nse_symbol")["security_id"]
        df.loc[:, "security_id"] = df["_norm_symbol"].map(security_lookup)

        unresolved = df["security_id"].isna()
        if unresolved.any():
            df = QualityMetadata.flag_unresolved_symbols(df, unresolved)

        # Normalise action type → canonical code
        df.loc[:, "action_code"] = df[action_col].apply(FN.normalize_action_type)

        # Normalise dates
        df.loc[:, "event_date"] = (
            df[exdate_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
        )
        df.loc[:, "record_date"] = (
            df[recdate_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if recdate_col
            else None
        )
        df.loc[:, "payment_date"] = (
            df[paydate_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if paydate_col
            else None
        )

        # Normalise value/ratio
        df.loc[:, "old_value"] = (
            df[value_col].apply(FN.normalize_numeric) if value_col else None
        )
        df.loc[:, "new_value"] = None  # populated by adjustment pipeline (Task 8)
        df.loc[:, "adjustment_factor"] = None  # populated by adjustment pipeline (Task 8)

        # Confidence score comes from QualityMetadata
        df = self._qm.add_quality_flags(df)

        # Rename _confidence_score → confidence_score to match schema
        df.rename(columns={"_confidence_score": "confidence_score"}, inplace=True)

        # Drop working columns
        df.drop(
            columns=["_norm_symbol", "_unresolved_symbol"],
            errors="ignore",
            inplace=True,
        )

        out_cols = [
            "security_id",
            "action_code",
            "event_date",
            "record_date",
            "payment_date",
            "old_value",
            "new_value",
            "adjustment_factor",
            "confidence_score",
            "_source_file",
            "_extracted_date",
            "_quality_issues",
            "_manual_review_required",
        ]
        return df[[c for c in out_cols if c in df.columns]]

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        """Return the first candidate column name present in df, or None."""
        for col in candidates:
            if col in df.columns:
                return col
        return None
