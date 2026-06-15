"""
NSE–BSE cross-exchange ISIN bridge.

Joins NSE symbol history and BSE scrip history on ISIN to produce a unified
cross-exchange entity table (fact_exchange_security_map).

Key outputs:
  - Dual-listed securities: ISIN appears on both NSE and BSE
  - BSE-only listings: ISIN in BSE master but not in NSE master
  - NSE-only listings: ISIN in NSE master but not in BSE master
  - Corporate action date conflicts: same ISIN, different ex_date across
    exchanges — a high-value data quality signal for buyers

This module is deliberately read-only (pure transformation). It does not
write to disk or Dolt; that is the run.py / dolt_importer responsibility.
"""

import pandas as pd


class ISINBridgeBuilder:
    """
    Builds the fact_exchange_security_map cross-exchange entity table.

    Usage:
        builder = ISINBridgeBuilder()
        bridge = builder.build(
            nse_securities=dim_security_master_df,
            bse_scrips=dim_bse_scrip_master_df,
        )
        conflicts = builder.find_ca_date_conflicts(
            nse_actions=nse_fact_ca_df,
            bse_actions=bse_fact_ca_df,
            bridge=bridge,
        )
    """

    # ── primary bridge builder ────────────────────────────────────────────────

    def build(
        self,
        nse_securities: pd.DataFrame,
        bse_scrips: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Join NSE and BSE security masters on ISIN to build the cross-exchange map.

        Each output row represents one ISIN (one legal entity), carrying:
          - its NSE symbol and listing period (if listed on NSE)
          - its BSE scrip code and listing period (if listed on BSE)
          - flags: is_bse_only, is_nse_only

        Args:
            nse_securities: dim_security_master DataFrame with columns:
                            nse_symbol, isin, listing_date, active_flag
            bse_scrips:     dim_bse_scrip_master DataFrame with columns:
                            scrip_code, isin, listing_date, active_flag

        Returns:
            DataFrame matching fact_exchange_security_map schema (migration 002).
        """
        nse = self._prep_nse(nse_securities)
        bse = self._prep_bse(bse_scrips)

        # Outer join on ISIN — keeps BSE-only and NSE-only ISINs
        merged = pd.merge(nse, bse, on="isin", how="outer", suffixes=("_nse", "_bse"))

        merged["is_bse_only"] = (
            merged["nse_symbol"].isna() & merged["bse_scrip_code"].notna()
        )
        merged["is_nse_only"] = (
            merged["bse_scrip_code"].isna() & merged["nse_symbol"].notna()
        )
        merged["ca_date_conflict"] = False  # populated by find_ca_date_conflicts()

        merged["map_id"] = range(1, len(merged) + 1)

        out_cols = [
            "map_id",
            "isin",
            "nse_symbol",
            "nse_effective_from",
            "nse_effective_to",
            "bse_scrip_code",
            "bse_effective_from",
            "bse_effective_to",
            "is_bse_only",
            "is_nse_only",
            "ca_date_conflict",
        ]
        return merged[[c for c in out_cols if c in merged.columns]].reset_index(
            drop=True
        )

    # ── corporate action date conflict finder ─────────────────────────────────

    def find_ca_date_conflicts(
        self,
        nse_actions: pd.DataFrame,
        bse_actions: pd.DataFrame,
        bridge: pd.DataFrame,
        tolerance_days: int = 3,
    ) -> pd.DataFrame:
        """
        Identify ISINs where NSE and BSE disagree on a corporate action date.

        For each ISIN that appears in both NSE and BSE corporate action tables,
        finds cases where the ex_date for the same action type differs by more
        than `tolerance_days`. This is a strong signal of a data quality issue
        in either exchange feed and a differentiating value proposition for buyers.

        Args:
            nse_actions: fact_corporate_action_event (NSE) with isin or
                         nse_symbol column plus action_code and event_date
            bse_actions: fact_corporate_action_event (BSE) with scrip_code
                         or isin column plus action_code and event_date
            bridge:      output of build() — used to join scrip_code → ISIN
            tolerance_days: date difference (in days) above which a conflict
                            is flagged (default: 3 days)

        Returns:
            DataFrame of conflicts with columns:
                isin, action_code, nse_ex_date, bse_ex_date,
                date_diff_days, conflict_severity
        """
        # Resolve ISIN in NSE actions (may have nse_symbol, need isin)
        nse = self._enrich_with_isin_nse(nse_actions, bridge)
        bse = self._enrich_with_isin_bse(bse_actions, bridge)

        if nse.empty or bse.empty:
            return pd.DataFrame(
                columns=[
                    "isin",
                    "action_code",
                    "nse_ex_date",
                    "bse_ex_date",
                    "date_diff_days",
                    "conflict_severity",
                ]
            )

        # Join on ISIN + action_code
        joined = pd.merge(
            nse[["isin", "action_code", "event_date"]].rename(
                columns={"event_date": "nse_ex_date"}
            ),
            bse[["isin", "action_code", "event_date"]].rename(
                columns={"event_date": "bse_ex_date"}
            ),
            on=["isin", "action_code"],
            how="inner",
        )

        if joined.empty:
            return pd.DataFrame(
                columns=[
                    "isin",
                    "action_code",
                    "nse_ex_date",
                    "bse_ex_date",
                    "date_diff_days",
                    "conflict_severity",
                ]
            )

        joined["nse_ex_date"] = pd.to_datetime(joined["nse_ex_date"], errors="coerce")
        joined["bse_ex_date"] = pd.to_datetime(joined["bse_ex_date"], errors="coerce")
        joined["date_diff_days"] = (
            joined["nse_ex_date"] - joined["bse_ex_date"]
        ).dt.days.abs()

        conflicts = joined[joined["date_diff_days"] > tolerance_days].copy()
        conflicts["conflict_severity"] = conflicts["date_diff_days"].apply(
            self._severity
        )

        conflicts.sort_values("date_diff_days", ascending=False, inplace=True)
        return conflicts.reset_index(drop=True)

    # ── summary helpers ────────────────────────────────────────────────────────

    def summarize(self, bridge: pd.DataFrame) -> dict:
        """
        Return a summary dict of the bridge table for logging and release notes.

        Keys:
            total_isins, dual_listed, bse_only, nse_only, ca_conflicts
        """
        return {
            "total_isins": len(bridge),
            "dual_listed": int((~bridge["is_bse_only"] & ~bridge["is_nse_only"]).sum()),
            "bse_only": int(bridge["is_bse_only"].sum()),
            "nse_only": int(bridge["is_nse_only"].sum()),
            "ca_conflicts": int(bridge.get("ca_date_conflict", pd.Series(False)).sum()),
        }

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _prep_nse(df: pd.DataFrame) -> pd.DataFrame:
        nse = df.copy()
        isin_col = next((c for c in ["isin", "ISIN"] if c in nse.columns), None)
        sym_col = next((c for c in ["nse_symbol", "SYMBOL"] if c in nse.columns), None)
        date_col = next(
            (c for c in ["listing_date", "LISTING_DATE"] if c in nse.columns), None
        )

        if isin_col is None:
            raise ValueError("NSE securities DataFrame missing 'isin' column")

        result = pd.DataFrame()
        result["isin"] = nse[isin_col].astype(str).str.strip().str.upper()
        result.loc[result["isin"].isin(["NAN", "NONE", ""]), "isin"] = None
        result["nse_symbol"] = nse[sym_col] if sym_col else None
        result["nse_effective_from"] = nse[date_col] if date_col else None
        result["nse_effective_to"] = None

        return result.dropna(subset=["isin"])

    @staticmethod
    def _prep_bse(df: pd.DataFrame) -> pd.DataFrame:
        bse = df.copy()
        isin_col = next((c for c in ["isin", "ISIN"] if c in bse.columns), None)
        code_col = next(
            (c for c in ["scrip_code", "SCRIP_CODE"] if c in bse.columns), None
        )
        date_col = next(
            (c for c in ["listing_date", "LISTING_DATE"] if c in bse.columns), None
        )

        if isin_col is None:
            raise ValueError("BSE scrips DataFrame missing 'isin' column")

        result = pd.DataFrame()
        result["isin"] = bse[isin_col].astype(str).str.strip().str.upper()
        result.loc[result["isin"].isin(["NAN", "NONE", ""]), "isin"] = None
        result["bse_scrip_code"] = bse[code_col] if code_col else None
        result["bse_effective_from"] = bse[date_col] if date_col else None
        result["bse_effective_to"] = None

        return result.dropna(subset=["isin"])

    @staticmethod
    def _enrich_with_isin_nse(
        nse_actions: pd.DataFrame, bridge: pd.DataFrame
    ) -> pd.DataFrame:
        """Add 'isin' to NSE actions if missing, using bridge as lookup."""
        df = nse_actions.copy()
        if "isin" not in df.columns and "nse_symbol" in df.columns:
            sym_to_isin = bridge.dropna(subset=["nse_symbol"]).set_index("nse_symbol")[
                "isin"
            ]
            df["isin"] = df["nse_symbol"].map(sym_to_isin)
        elif "isin" not in df.columns and "SYMBOL" in df.columns:
            sym_to_isin = bridge.dropna(subset=["nse_symbol"]).set_index("nse_symbol")[
                "isin"
            ]
            df["isin"] = df["SYMBOL"].map(sym_to_isin)
        return df.dropna(subset=["isin"])

    @staticmethod
    def _enrich_with_isin_bse(
        bse_actions: pd.DataFrame, bridge: pd.DataFrame
    ) -> pd.DataFrame:
        """Add 'isin' to BSE actions if missing, using bridge as lookup."""
        df = bse_actions.copy()
        if "isin" not in df.columns and "scrip_id" in df.columns:
            # scrip_id → scrip_code → isin via bridge
            pass  # isin should already be resolved upstream; no-op
        if "isin" not in df.columns and "SCRIP_CODE" in df.columns:
            code_to_isin = bridge.dropna(subset=["bse_scrip_code"]).set_index(
                "bse_scrip_code"
            )["isin"]
            df["isin"] = df["SCRIP_CODE"].map(code_to_isin)
        return df.dropna(subset=["isin"])

    @staticmethod
    def _severity(diff_days: int) -> str:
        if diff_days > 30:
            return "HIGH"
        elif diff_days > 7:
            return "MEDIUM"
        else:
            return "LOW"
