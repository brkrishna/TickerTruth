"""
BSE adjustment factor builder.

Adapts BSE corporate action events (keyed by scrip_id from dim_bse_scrip_master)
into the same AdjustmentFactorBuilder pipeline used for NSE. Also provides a
cross-validation function that compares BSE vs. NSE adjustment factors for
dual-listed securities using the ISIN bridge.

Key difference from NSE: primary key is scrip_id (BSE) vs. security_id (NSE).
The adapter renames the column before delegation so the core calculator is reused.
"""

import logging

import pandas as pd

from pipelines.adjustments.adjuster import AdjustmentFactorBuilder

log = logging.getLogger(__name__)

# Maximum acceptable factor discrepancy between NSE and BSE for same ISIN/date.
# Differences beyond this are flagged as data quality issues.
_FACTOR_TOLERANCE = 0.001

# Severity thresholds (multiplicative divergence from expected)
_SEVERITY_HIGH = 0.05  # > 5% divergence
_SEVERITY_MEDIUM = 0.01  # > 1% divergence


class BSEAdjustmentFactorBuilder:
    """
    Builds fact_adjustment_factor rows from BSE corporate action events.

    Delegates computation to AdjustmentFactorBuilder (shared with NSE).
    The only BSE-specific adaptation is the scrip_id → security_id rename.

    Usage:
        builder = BSEAdjustmentFactorBuilder()
        bse_factors = builder.build_from_bse_actions(bse_ca_df, dim_bse_scrip_df)
        discrepancies = builder.cross_validate_with_nse(bse_factors, nse_factors, bridge_df)
    """

    def __init__(self) -> None:
        self._inner = AdjustmentFactorBuilder()

    # ── primary build ─────────────────────────────────────────────────────────

    def build_from_bse_actions(
        self,
        bse_actions: pd.DataFrame,
        dim_bse_scrip: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute cumulative adjustment factors from BSE corporate action events.

        Expects bse_actions to have a scrip_id column (output of
        BSERawToCanonicalMapper.map_to_fact_bse_corporate_action_event()).
        Internally renames scrip_id → security_id so AdjustmentFactorBuilder
        can be reused without modification.

        Args:
            bse_actions:   fact_corporate_action_event DataFrame for BSE with
                           columns: scrip_id, action_code, event_date, old_value
            dim_bse_scrip: dim_bse_scrip_master DataFrame (for scrip_code lookup)

        Returns:
            fact_adjustment_factor DataFrame with one row per (scrip_id, as_of_date)
            where a SPLIT or BONUS occurred. Adds scrip_code column for traceability.
        """
        if bse_actions.empty:
            return pd.DataFrame(
                columns=[
                    "scrip_id",
                    "scrip_code",
                    "as_of_date",
                    "cumulative_split_adjustment",
                    "cumulative_bonus_adjustment",
                    "cumulative_dividend_adjustment",
                    "total_adjustment_factor",
                ]
            )

        # Resolve scrip_id if missing — use scrip_code → scrip_id from dim table
        actions = bse_actions.copy()
        if "scrip_id" not in actions.columns:
            if "scrip_code" not in actions.columns:
                raise ValueError(
                    "bse_actions must have 'scrip_id' or 'scrip_code' column"
                )
            code_to_id = dim_bse_scrip.set_index("scrip_code")["scrip_id"]
            actions["scrip_id"] = actions["scrip_code"].map(code_to_id)

        # Adapter: rename scrip_id → security_id to reuse the shared builder
        adapted = actions.rename(columns={"scrip_id": "security_id"})

        # Delegate to shared AdjustmentFactorBuilder
        result = self._inner.build_from_corporate_actions(
            actions=adapted,
            symbols=dim_bse_scrip,
        )

        if result.empty:
            return pd.DataFrame(
                columns=[
                    "scrip_id",
                    "scrip_code",
                    "as_of_date",
                    "cumulative_split_adjustment",
                    "cumulative_bonus_adjustment",
                    "cumulative_dividend_adjustment",
                    "total_adjustment_factor",
                ]
            )

        # Rename back security_id → scrip_id
        result.rename(columns={"security_id": "scrip_id"}, inplace=True)

        # Re-attach scrip_code for traceability
        if "scrip_id" in result.columns and "scrip_code" in dim_bse_scrip.columns:
            id_to_code = dim_bse_scrip.set_index("scrip_id")["scrip_code"]
            result["scrip_code"] = result["scrip_id"].map(id_to_code)

        col_order = [
            "scrip_id",
            "scrip_code",
            "as_of_date",
            "cumulative_split_adjustment",
            "cumulative_bonus_adjustment",
            "cumulative_dividend_adjustment",
            "total_adjustment_factor",
        ]
        return result[[c for c in col_order if c in result.columns]]

    # ── cross-validation ──────────────────────────────────────────────────────

    def cross_validate_with_nse(
        self,
        bse_factors: pd.DataFrame,
        nse_factors: pd.DataFrame,
        bridge: pd.DataFrame,
        tolerance: float = _FACTOR_TOLERANCE,
    ) -> pd.DataFrame:
        """
        Compare BSE and NSE adjustment factors for dual-listed securities.

        For each ISIN that has adjustment factors on both exchanges, joins
        by event date and flags discrepancies. A discrepancy signals either
        a data error in one feed, or a genuine exchange-specific event
        (rare but possible for rights issues).

        Args:
            bse_factors: output of build_from_bse_actions() with scrip_id column
            nse_factors: fact_adjustment_factor for NSE with security_id column
            bridge:      output of ISINBridgeBuilder.build() with columns
                         nse_symbol, bse_scrip_code, isin
            tolerance:   absolute tolerance for factor comparison (default 0.001)

        Returns:
            DataFrame of discrepancies with columns:
                isin, as_of_date,
                bse_total_factor, nse_total_factor,
                factor_diff, discrepancy_severity
        """
        if bse_factors.empty or nse_factors.empty or bridge.empty:
            return pd.DataFrame(
                columns=[
                    "isin",
                    "as_of_date",
                    "bse_total_factor",
                    "nse_total_factor",
                    "factor_diff",
                    "discrepancy_severity",
                ]
            )

        # Build ISIN → scrip_id lookup from bridge + dim tables
        bse_with_isin = self._attach_isin_to_bse(bse_factors, bridge)
        nse_with_isin = self._attach_isin_to_nse(nse_factors, bridge)

        if bse_with_isin.empty or nse_with_isin.empty:
            return pd.DataFrame(
                columns=[
                    "isin",
                    "as_of_date",
                    "bse_total_factor",
                    "nse_total_factor",
                    "factor_diff",
                    "discrepancy_severity",
                ]
            )

        # Join on ISIN + as_of_date
        joined = pd.merge(
            bse_with_isin[["isin", "as_of_date", "total_adjustment_factor"]].rename(
                columns={"total_adjustment_factor": "bse_total_factor"}
            ),
            nse_with_isin[["isin", "as_of_date", "total_adjustment_factor"]].rename(
                columns={"total_adjustment_factor": "nse_total_factor"}
            ),
            on=["isin", "as_of_date"],
            how="inner",
        )

        if joined.empty:
            return pd.DataFrame(
                columns=[
                    "isin",
                    "as_of_date",
                    "bse_total_factor",
                    "nse_total_factor",
                    "factor_diff",
                    "discrepancy_severity",
                ]
            )

        joined["factor_diff"] = (
            joined["bse_total_factor"] - joined["nse_total_factor"]
        ).abs()

        discrepancies = joined[joined["factor_diff"] > tolerance].copy()
        discrepancies["discrepancy_severity"] = discrepancies["factor_diff"].apply(
            self._severity
        )
        discrepancies.sort_values("factor_diff", ascending=False, inplace=True)

        log.info(
            "BSE/NSE factor cross-validation: %d dual-listed pairs checked, "
            "%d discrepancies found",
            len(joined),
            len(discrepancies),
        )

        return discrepancies.reset_index(drop=True)

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _attach_isin_to_bse(
        bse_factors: pd.DataFrame,
        bridge: pd.DataFrame,
    ) -> pd.DataFrame:
        """Join BSE factors with ISIN via bridge (bse_scrip_code → ISIN)."""
        bse = bse_factors.copy()
        if "scrip_code" not in bse.columns:
            return pd.DataFrame()

        code_to_isin = (
            bridge.dropna(subset=["bse_scrip_code", "isin"])
            .drop_duplicates("bse_scrip_code")
            .set_index("bse_scrip_code")["isin"]
        )
        bse["isin"] = bse["scrip_code"].map(code_to_isin)
        return bse.dropna(subset=["isin"])

    @staticmethod
    def _attach_isin_to_nse(
        nse_factors: pd.DataFrame,
        bridge: pd.DataFrame,
    ) -> pd.DataFrame:
        """Join NSE factors with ISIN via bridge (nse_symbol → ISIN)."""
        nse = nse_factors.copy()
        if "security_id" not in nse.columns:
            return pd.DataFrame()

        # bridge may carry nse_symbol; we need security_id→ISIN via symbol
        # If bridge has nse_symbol and the NSE factors have security_id,
        # we use nse_symbol as the join key if security_id == symbol (text key).
        # For numeric security_id, the caller must pass bridge with security_id col.
        if "nse_symbol" in bridge.columns and "security_id" not in bridge.columns:
            sym_to_isin = (
                bridge.dropna(subset=["nse_symbol", "isin"])
                .drop_duplicates("nse_symbol")
                .set_index("nse_symbol")["isin"]
            )
            # Try treating security_id as a symbol string
            nse["isin"] = nse["security_id"].astype(str).map(sym_to_isin)
        elif "security_id" in bridge.columns:
            id_to_isin = (
                bridge.dropna(subset=["security_id", "isin"])
                .drop_duplicates("security_id")
                .set_index("security_id")["isin"]
            )
            nse["isin"] = nse["security_id"].map(id_to_isin)
        else:
            return pd.DataFrame()

        return nse.dropna(subset=["isin"])

    @staticmethod
    def _severity(diff: float) -> str:
        if diff > _SEVERITY_HIGH:
            return "HIGH"
        elif diff > _SEVERITY_MEDIUM:
            return "MEDIUM"
        else:
            return "LOW"
