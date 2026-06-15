"""
Maps BSE staging DataFrames to canonical Dolt schema tables.

Mirrors the NSE RawToCanonicalMapper pattern but handles BSE-specific fields:
  - SCRIP_CODE (numeric string) as primary key instead of SYMBOL
  - 'purpose' field for action types (different vocabulary from NSE 'subject')
  - STATUS column present in BSE (unlike NSE EQUITY_L.csv)
  - BSE often omits ex_date for dividends — flagged with LOW confidence

Output DataFrames target:
  - dim_bse_scrip_master  (from bse_scrips_consolidated.csv)
  - fact_corporate_action_event (same schema as NSE — keyed via scrip → ISIN → security_id)
"""

import yaml
from pathlib import Path

import pandas as pd

from pipelines.normalize.normalizers import FieldNormalizer as FN
from pipelines.normalize.quality import QualityMetadata

_FIELD_MAPPINGS_PATH = Path(__file__).parent / "field_mappings.yaml"

BSE_EXCHANGE_ID = 2


def _load_bse_action_map() -> dict[str, str]:
    """Load bse_action_type_mapping from field_mappings.yaml."""
    with open(_FIELD_MAPPINGS_PATH) as f:
        data = yaml.safe_load(f)
    return {k.lower(): v for k, v in data.get("bse_action_type_mapping", {}).items()}


_BSE_ACTION_MAP: dict[str, str] = _load_bse_action_map()


def normalize_bse_action_type(purpose: str) -> str:
    """
    Map a raw BSE 'purpose' string to a canonical action code.

    Uses bse_action_type_mapping from field_mappings.yaml for exact matches,
    then falls back to substring matching. Returns "UNKNOWN" if no match.

    Unlike NSE's 'subject' field, BSE 'purpose' is more standardised but
    still contains free-text variants like "Dividend - Rs.2.00 per share".
    """
    if not purpose or not isinstance(purpose, str):
        return "UNKNOWN"

    key = purpose.strip().lower()

    if key in _BSE_ACTION_MAP:
        return _BSE_ACTION_MAP[key]

    # Substring match for decorated strings like "Interim Dividend - Rs.5.00"
    for raw_key, canonical in _BSE_ACTION_MAP.items():
        if raw_key in key:
            return canonical

    # Fall back to NSE FieldNormalizer — shares much of the same vocabulary
    return FN.normalize_action_type(purpose)


class BSERawToCanonicalMapper:
    """
    Maps BSE staging DataFrames to canonical schema-aligned DataFrames.

    Typical call sequence:
        mapper = BSERawToCanonicalMapper(source_file="bse_scrips_consolidated.csv")
        dim_bse  = mapper.map_to_dim_bse_scrip_master(raw_scrips)
        fact_ca  = mapper.map_to_fact_bse_corporate_action_event(raw_actions, dim_bse)
    """

    def __init__(self, source_file: str = ""):
        self._qm = QualityMetadata(source_file=source_file)

    # ── dim_bse_scrip_master ───────────────────────────────────────────────────

    def map_to_dim_bse_scrip_master(self, raw_scrips: pd.DataFrame) -> pd.DataFrame:
        """
        Build dim_bse_scrip_master from BSE scrips staging data.

        Normalises scrip codes, company names, ISINs, dates, and status flags.
        Each row corresponds to one BSE scrip code (one row per scrip_code).

        Output columns (match dim_bse_scrip_master in migration 002):
            scrip_id, scrip_code, isin, scrip_name, company_name,
            segment, listing_date, active_flag

        Args:
            raw_scrips: consolidated BSE scrips staging DataFrame.

        Returns:
            dim_bse_scrip_master DataFrame.
        """
        df = raw_scrips.copy()

        code_col = self._find_col(df, ["SCRIP_CODE", "SC_CD", "Scrip_Cd"])
        name_col = self._find_col(df, ["SCRIP_NAME", "SC_NAME"])
        company_col = self._find_col(df, ["COMPANY_NAME"])
        isin_col = self._find_col(df, ["ISIN", "ISIN_CODE"])
        date_col = self._find_col(df, ["LISTING_DATE", "DT_DATE"])
        status_col = self._find_col(df, ["STATUS", "Status"])
        segment_col = self._find_col(df, ["SEGMENT", "GROUP", "Segment"])

        if code_col is None:
            raise ValueError(
                f"raw_scrips missing SCRIP_CODE column. Got: {list(df.columns)}"
            )

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "scrip_id",
                    "scrip_code",
                    "isin",
                    "scrip_name",
                    "company_name",
                    "segment",
                    "listing_date",
                    "active_flag",
                    "_source_file",
                    "_extracted_date",
                    "_quality_issues",
                    "_confidence_score",
                    "_manual_review_required",
                ]
            )

        # Scrip code — zero-pad to 6 digits, always string
        df["scrip_code"] = df[code_col].astype(str).str.strip().str.zfill(6)

        # Scrip name (short, ≤12 chars per BSE convention)
        df["scrip_name"] = (
            df[name_col].astype(str).str.strip().str.upper() if name_col else ""
        )

        # Company name — full normalised form
        df["company_name"] = (
            df[company_col].apply(FN.normalize_company_name)
            if company_col
            else df["scrip_name"]
        )

        # ISIN
        df["isin"] = (
            df[isin_col].astype(str).str.strip().str.upper() if isin_col else None
        )
        if "isin" in df.columns:
            df.loc[df["isin"].isin(["NAN", "NONE", ""]), "isin"] = None

        # Segment
        df["segment"] = (
            df[segment_col].astype(str).str.strip().str.upper() if segment_col else "EQ"
        )

        # Listing date
        df["listing_date"] = (
            df[date_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if date_col
            else None
        )

        # Active flag from STATUS
        df["active_flag"] = True
        if status_col:
            inactive = (
                df[status_col]
                .astype(str)
                .str.lower()
                .isin(["delisted", "suspended", "inactive", "unlisted", "0"])
            )
            df.loc[inactive, "active_flag"] = False

        # Dedup on scrip_code (keep last — most recent)
        df.drop_duplicates(subset=["scrip_code"], keep="last", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df["scrip_id"] = df.index + 1

        df = self._qm.add_quality_flags(df)

        out_cols = [
            "scrip_id",
            "scrip_code",
            "isin",
            "scrip_name",
            "company_name",
            "segment",
            "listing_date",
            "active_flag",
            "_source_file",
            "_extracted_date",
            "_quality_issues",
            "_confidence_score",
            "_manual_review_required",
        ]
        return df[[c for c in out_cols if c in df.columns]]

    # ── fact_corporate_action_event (BSE) ────────────────────────────────────

    def map_to_fact_bse_corporate_action_event(
        self,
        raw_actions: pd.DataFrame,
        dim_bse_scrip: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build fact_corporate_action_event rows from BSE corporate actions.

        Resolves scrip_id via SCRIP_CODE join on dim_bse_scrip_master.
        Normalises BSE-specific action type strings via normalize_bse_action_type().

        BSE-specific confidence adjustments:
          - Missing ex_date (common for BSE dividends): penalty applied
          - action_code = UNKNOWN: LOW confidence flag

        Output columns (same schema as NSE fact_corporate_action_event):
            scrip_id, action_code, event_date, record_date, payment_date,
            old_value, new_value, adjustment_factor, confidence_score,
            confidence_flag, exchange_id

        Args:
            raw_actions:    consolidated BSE corporate actions staging DataFrame.
            dim_bse_scrip:  output of map_to_dim_bse_scrip_master().

        Returns:
            fact_corporate_action_event DataFrame for BSE (exchange_id = 2).
        """
        df = raw_actions.copy()

        code_col = self._find_col(df, ["SCRIP_CODE", "SC_CD", "scrip_code"])
        action_col = self._find_col(df, ["ACTION_TYPE_RAW", "Purpose", "purpose"])
        exdate_col = self._find_col(df, ["EX_DATE", "ExDate", "ex_date"])
        recdate_col = self._find_col(df, ["RECORD_DATE", "RdDate", "record_date"])
        paydate_col = self._find_col(df, ["PAYMENT_DATE", "PdDate", "payment_date"])
        value_col = self._find_col(df, ["VALUE_OR_RATIO", "VALUE", "FACE_VALUE"])

        if code_col is None or action_col is None:
            raise ValueError(
                "raw_actions missing required columns. "
                f"Need SCRIP_CODE, ACTION_TYPE_RAW. Got: {list(df.columns)}"
            )

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "scrip_id",
                    "action_code",
                    "event_date",
                    "record_date",
                    "payment_date",
                    "old_value",
                    "new_value",
                    "adjustment_factor",
                    "confidence_score",
                    "confidence_flag",
                    "exchange_id",
                    "_source_file",
                    "_extracted_date",
                    "_quality_issues",
                    "_manual_review_required",
                ]
            )

        # Normalise scrip_code and resolve scrip_id
        df["_norm_code"] = df[code_col].astype(str).str.strip().str.zfill(6)
        scrip_lookup = dim_bse_scrip.set_index("scrip_code")["scrip_id"]
        df["scrip_id"] = df["_norm_code"].map(scrip_lookup)

        unresolved = df["scrip_id"].isna()
        if unresolved.any():
            df = QualityMetadata.flag_unresolved_symbols(df, unresolved)

        # Normalise action type using BSE-specific vocabulary
        df["action_code"] = df[action_col].apply(normalize_bse_action_type)

        # Normalise dates
        df["event_date"] = (
            df[exdate_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if exdate_col
            else None
        )
        df["record_date"] = (
            df[recdate_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if recdate_col
            else None
        )
        df["payment_date"] = (
            df[paydate_col]
            .apply(FN.normalize_date)
            .apply(lambda d: d.isoformat() if d else None)
            if paydate_col
            else None
        )

        # Numeric value / ratio
        df["old_value"] = (
            df[value_col].apply(FN.normalize_numeric) if value_col else None
        )
        df["new_value"] = None
        df["adjustment_factor"] = None

        # Mark BSE exchange
        df["exchange_id"] = BSE_EXCHANGE_ID

        # Apply quality flags (base scorer handles missing fields)
        df = self._qm.add_quality_flags(df)

        # BSE-specific confidence penalty: missing ex_date is common but lowers trust
        missing_exdate = df["event_date"].isna()
        if missing_exdate.any():
            df.loc[missing_exdate, "_confidence_score"] = (
                df.loc[missing_exdate, "_confidence_score"] - 0.15
            ).clip(lower=0.0)
            existing = df.loc[missing_exdate, "_quality_issues"].fillna("")
            df.loc[missing_exdate, "_quality_issues"] = existing.apply(
                lambda v: f"{v},BSE_MISSING_EX_DATE" if v else "BSE_MISSING_EX_DATE"
            )

        df.rename(columns={"_confidence_score": "confidence_score"}, inplace=True)
        df["confidence_flag"] = df["confidence_score"].apply(
            QualityMetadata.score_to_flag
        )

        df.drop(
            columns=["_norm_code", "_unresolved_symbol"],
            errors="ignore",
            inplace=True,
        )

        out_cols = [
            "scrip_id",
            "action_code",
            "event_date",
            "record_date",
            "payment_date",
            "old_value",
            "new_value",
            "adjustment_factor",
            "confidence_score",
            "confidence_flag",
            "exchange_id",
            "_source_file",
            "_extracted_date",
            "_quality_issues",
            "_manual_review_required",
        ]
        return df[[c for c in out_cols if c in df.columns]]

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        for col in candidates:
            if col in df.columns:
                return col
        return None
