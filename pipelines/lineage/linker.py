"""
SymbolLinker — compares symbol snapshots across time periods to produce
lineage events, then cross-references those events with corporate actions
to boost confidence and flag gaps for manual review.
"""

from datetime import timedelta

import pandas as pd

from pipelines.lineage.rules import LineageEvent, LineageRulesEngine

# Days within which a corporate action must fall to corroborate a lineage event
_CORROBORATION_WINDOW_DAYS = 30
_CORROBORATION_BOOST       = 0.15
_CORROBORATING_ACTION_CODES = frozenset({"MERGER", "DEMERGER", "DELISTING", "AMALGAMATION"})


class SymbolLinker:
    """
    Compares NSE symbol snapshots across time periods to detect lineage events.

    Usage:
        linker = SymbolLinker()
        events_df = linker.link_across_periods(current_df, historical_df, period_date)
        events_df = linker.cross_reference_with_actions(events_df, actions_df)
    """

    def __init__(self):
        self._engine = LineageRulesEngine()

    # ── primary linker ────────────────────────────────────────────────────────

    def link_across_periods(
        self,
        current_symbols: pd.DataFrame,
        historical_symbols: pd.DataFrame,
        period_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """
        Compare two symbol snapshots and produce a DataFrame of lineage events.

        Detects:
          - LISTING    — symbol in current but not in historical
          - DELISTING  — symbol in historical but not in current (no ISIN match)
          - RENAME     — same ISIN, different symbol across snapshots

        Args:
            current_symbols:    DataFrame with at least SYMBOL column; optional ISIN
            historical_symbols: DataFrame with at least SYMBOL column; optional ISIN
            period_date:        Date to assign to inferred events; defaults to today

        Returns:
            DataFrame of LineageEvent.to_dict() rows, sorted by event_date.
        """
        if period_date is None:
            period_date = pd.Timestamp.today().date()
        elif hasattr(period_date, "date"):
            period_date = period_date.date()

        current_syms    = set(current_symbols["SYMBOL"].dropna().str.strip().str.upper())
        historical_syms = set(historical_symbols["SYMBOL"].dropna().str.strip().str.upper())

        events: list[dict] = []

        # ── new listings ──────────────────────────────────────────────────────
        for sym in current_syms - historical_syms:
            ev = LineageEvent(
                event_type="LISTING",
                event_date=period_date,
                confidence=0.95,
                symbol_from=None,
                symbol_to=sym,
                reason=f"{sym} appeared in active list (new listing or recovery)",
                corroborating_evidence=["symbol_absent_in_historical_snapshot"],
            )
            events.append(ev.to_dict())

        # ── removals — may be delisting or rename ─────────────────────────────
        removed = historical_syms - current_syms

        # Build ISIN → symbol lookup for the current snapshot (for rename detection)
        isin_to_current: dict[str, str] = {}
        if "ISIN" in current_symbols.columns:
            for _, row in current_symbols.iterrows():
                isin = str(row.get("ISIN", "")).strip().upper()
                sym  = str(row.get("SYMBOL", "")).strip().upper()
                if isin and isin != "NAN":
                    isin_to_current[isin] = sym

        # Build symbol → ISIN for historical
        hist_sym_to_isin: dict[str, str] = {}
        if "ISIN" in historical_symbols.columns:
            for _, row in historical_symbols.iterrows():
                sym  = str(row.get("SYMBOL", "")).strip().upper()
                isin = str(row.get("ISIN", "")).strip().upper()
                if sym and isin and isin != "NAN":
                    hist_sym_to_isin[sym] = isin

        for sym in removed:
            isin = hist_sym_to_isin.get(sym)
            new_sym = isin_to_current.get(isin) if isin else None

            if new_sym and new_sym != sym:
                # Same ISIN found under a different symbol → RENAME
                ev = self._engine.detect_symbol_rename(
                    prev_symbol=sym,
                    new_symbol=new_sym,
                    event_date=period_date,
                )
                ev.corroborating_evidence.append("isin_matched_across_snapshots")
                ev.confidence = min(0.98, ev.confidence + 0.10)  # ISIN match boosts confidence
            else:
                # Symbol gone, ISIN not found in current → inferred delisting
                ev = self._engine.detect_delisting(
                    symbol=sym,
                    last_trading_date=period_date,
                    is_explicit=False,
                )

            events.append(ev.to_dict())

        if not events:
            return pd.DataFrame(columns=[
                "symbol_from", "symbol_to", "event_date", "event_type",
                "confidence", "reason", "corroborating_evidence",
            ])

        df = pd.DataFrame(events).sort_values("event_date").reset_index(drop=True)
        return df

    # ── cross-reference with corporate actions ────────────────────────────────

    def cross_reference_with_actions(
        self,
        lineage_events: pd.DataFrame,
        actions: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Boost confidence when a corporate action corroborates a lineage event,
        and flag events with no corroboration for manual review.

        For each DELISTING or MERGER lineage event, looks for a matching
        corporate action for the same symbol within ±30 days of the event date.

        Args:
            lineage_events: DataFrame from link_across_periods()
            actions:        fact_corporate_action_event DataFrame with columns
                            SYMBOL, action_code, event_date

        Returns:
            Updated lineage_events DataFrame with added columns:
              - corroborated (bool)
              - manual_review_required (bool)
        """
        if lineage_events.empty:
            lineage_events["corroborated"] = pd.Series(dtype=bool)
            lineage_events["manual_review_required"] = pd.Series(dtype=bool)
            return lineage_events

        events = lineage_events.copy()
        events["corroborated"]           = False
        events["manual_review_required"] = False

        # Only cross-reference events that benefit from corroboration
        needs_corroboration = events["event_type"].isin(["DELISTING", "MERGER", "DEMERGER"])

        if not needs_corroboration.any() or actions.empty:
            events.loc[needs_corroboration, "manual_review_required"] = True
            return events

        # Prepare actions lookup
        action_sym_col  = self._find_col(actions, ["SYMBOL", "symbol"])
        action_type_col = self._find_col(actions, ["action_code", "ACTION_CODE", "ACTION_TYPE_RAW"])
        action_date_col = self._find_col(actions, ["event_date", "EVENT_DATE", "EX_DATE"])

        if not all([action_sym_col, action_type_col, action_date_col]):
            events.loc[needs_corroboration, "manual_review_required"] = True
            return events

        # Convert dates for comparison
        events["_event_date_parsed"] = pd.to_datetime(events["event_date"], errors="coerce")
        actions["_action_date"]      = pd.to_datetime(actions[action_date_col], errors="coerce")

        window = timedelta(days=_CORROBORATION_WINDOW_DAYS)

        for idx in events[needs_corroboration].index:
            row        = events.loc[idx]
            ev_sym     = row.get("symbol_from") or row.get("symbol_to")
            ev_date    = row["_event_date_parsed"]

            if pd.isna(ev_date) or not ev_sym:
                events.loc[idx, "manual_review_required"] = True
                continue

            matching = actions[
                (actions[action_sym_col].str.upper() == str(ev_sym).upper()) &
                (actions[action_type_col].str.upper().isin(
                    {c.upper() for c in _CORROBORATING_ACTION_CODES}
                )) &
                (actions["_action_date"] >= ev_date - window) &
                (actions["_action_date"] <= ev_date + window)
            ]

            if not matching.empty:
                events.loc[idx, "corroborated"] = True
                boosted = min(0.99, row["confidence"] + _CORROBORATION_BOOST)
                events.loc[idx, "confidence"] = boosted
                ca_code = matching.iloc[0][action_type_col]
                ev_corr = row.get("corroborating_evidence", "")
                events.loc[idx, "corroborating_evidence"] = (
                    f"{ev_corr}; corp_action={ca_code}" if ev_corr else f"corp_action={ca_code}"
                )
            else:
                events.loc[idx, "manual_review_required"] = True

        events.drop(columns=["_event_date_parsed"], inplace=True)
        actions.drop(columns=["_action_date"], inplace=True, errors="ignore")
        return events

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        for col in candidates:
            if col in df.columns:
                return col
        return None
