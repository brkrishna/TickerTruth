"""
BSE scrip history and lineage reconstruction.

Compares BSE scrip master snapshots across time to detect per-scrip
lifecycle events: name changes, status transitions, and the rare but
documented case of a scrip code being retired and reassigned to a
different company.

Output targets fact_bse_scrip_lineage_event (migration 002).

Key differences from NSE lineage:
  - Primary key is SCRIP_CODE (numeric string), not a ticker symbol
  - ISIN is used to distinguish true delistings from code reassignments
  - BSE scrip name changes are more frequent than NSE symbol renames
    (BSE allows free-text short names up to 12 chars)
"""

from datetime import date

import pandas as pd


# Confidence levels for different evidence qualities
_CONFIDENCE_ISIN_MATCH = 0.95  # ISIN present in both snapshots → strong
_CONFIDENCE_NAME_CHANGE = 0.85  # same code, different name, same ISIN
_CONFIDENCE_CODE_REASSIGN = 0.80  # same code, different ISIN — code reuse
_CONFIDENCE_INFERRED = 0.65  # status change with no ISIN continuity


class BSEScripHistoryBuilder:
    """
    Reconstructs per-scrip lifecycle events by comparing BSE scrip snapshots.

    Usage:
        builder = BSEScripHistoryBuilder()
        events = builder.build_lineage_events(previous_df, current_df, event_date)
        status_history = builder.build_status_history(current_df, event_date)
    """

    # ── primary lineage detection ─────────────────────────────────────────────

    def build_lineage_events(
        self,
        previous: pd.DataFrame,
        current: pd.DataFrame,
        event_date: date | None = None,
    ) -> pd.DataFrame:
        """
        Compare two BSE scrip master snapshots and produce lineage events.

        Detects:
          LISTING       — scrip_code appears in current but not in previous
          DELISTING     — scrip_code in previous, absent in current, no ISIN
                          match in current (i.e. not a code reassignment)
          RENAME        — same scrip_code, same ISIN, different scrip_name
          CODE_REASSIGN — same scrip_code, different ISIN across snapshots
                          (the old entity delisted; a new one got the code)
          STATUS_CHANGE — scrip present in both, active_flag changed

        Args:
            previous:   dim_bse_scrip_master from prior period
            current:    dim_bse_scrip_master from current period
            event_date: date to assign to detected events (default: today)

        Returns:
            DataFrame of lineage events matching fact_bse_scrip_lineage_event schema.
        """
        if event_date is None:
            event_date = date.today()

        prev_codes = set(previous["scrip_code"].dropna().astype(str))
        curr_codes = set(current["scrip_code"].dropna().astype(str))

        # Build lookup maps for efficient comparison
        prev_map = self._build_scrip_map(previous)
        curr_map = self._build_scrip_map(current)

        events: list[dict] = []

        # New listings
        for code in curr_codes - prev_codes:
            events.append(
                self._make_event(
                    scrip_code=code,
                    event_type="LISTING",
                    event_date=event_date,
                    scrip_name_new=curr_map[code].get("scrip_name"),
                    confidence=_CONFIDENCE_ISIN_MATCH,
                )
            )

        # Removed scrip codes — could be delisting or code reassignment
        for code in prev_codes - curr_codes:
            prev_row = prev_map[code]
            prev_isin = prev_row.get("isin")

            # Check if the ISIN reappears under a different scrip code
            curr_isin_to_code = {
                r.get("isin"): c for c, r in curr_map.items() if r.get("isin")
            }
            reassigned_to = curr_isin_to_code.get(prev_isin) if prev_isin else None

            if reassigned_to and reassigned_to != code:
                # ISIN moved to a new code — this is not a delisting
                events.append(
                    self._make_event(
                        scrip_code=code,
                        event_type="DELISTING",
                        event_date=event_date,
                        scrip_name_old=prev_row.get("scrip_name"),
                        status_old="ACTIVE",
                        status_new="DELISTED",
                        confidence=_CONFIDENCE_ISIN_MATCH,
                    )
                )
            else:
                events.append(
                    self._make_event(
                        scrip_code=code,
                        event_type="DELISTING",
                        event_date=event_date,
                        scrip_name_old=prev_row.get("scrip_name"),
                        status_old="ACTIVE",
                        status_new="DELISTED",
                        confidence=_CONFIDENCE_INFERRED,
                    )
                )

        # Scrips present in both — check for renames, code reassignments, status changes
        for code in prev_codes & curr_codes:
            prev_row = prev_map[code]
            curr_row = curr_map[code]

            prev_isin = prev_row.get("isin")
            curr_isin = curr_row.get("isin")
            prev_name = prev_row.get("scrip_name", "")
            curr_name = curr_row.get("scrip_name", "")
            prev_active = prev_row.get("active_flag", True)
            curr_active = curr_row.get("active_flag", True)

            # Scrip code reassignment: same code, different ISIN
            if prev_isin and curr_isin and prev_isin != curr_isin:
                events.append(
                    self._make_event(
                        scrip_code=code,
                        event_type="CODE_REASSIGN",
                        event_date=event_date,
                        scrip_name_old=prev_name,
                        scrip_name_new=curr_name,
                        confidence=_CONFIDENCE_CODE_REASSIGN,
                    )
                )
                continue  # name/status changes are secondary to code reassignment

            # Name change: same ISIN, different scrip_name
            if prev_name and curr_name and prev_name != curr_name:
                events.append(
                    self._make_event(
                        scrip_code=code,
                        event_type="RENAME",
                        event_date=event_date,
                        scrip_name_old=prev_name,
                        scrip_name_new=curr_name,
                        confidence=_CONFIDENCE_NAME_CHANGE
                        if prev_isin == curr_isin
                        else _CONFIDENCE_INFERRED,
                    )
                )

            # Status change: active_flag flipped
            if bool(prev_active) != bool(curr_active):
                new_status = "ACTIVE" if curr_active else "DELISTED"
                old_status = "ACTIVE" if prev_active else "DELISTED"
                event_type = "RELISTING" if curr_active else "STATUS_CHANGE"
                events.append(
                    self._make_event(
                        scrip_code=code,
                        event_type=event_type,
                        event_date=event_date,
                        scrip_name_old=prev_name,
                        scrip_name_new=curr_name,
                        status_old=old_status,
                        status_new=new_status,
                        confidence=_CONFIDENCE_ISIN_MATCH
                        if prev_isin == curr_isin
                        else _CONFIDENCE_INFERRED,
                    )
                )

        if not events:
            return pd.DataFrame(
                columns=[
                    "scrip_code",
                    "event_type",
                    "effective_from",
                    "scrip_name_old",
                    "scrip_name_new",
                    "status_old",
                    "status_new",
                    "confidence",
                ]
            )

        df = pd.DataFrame(events).sort_values("effective_from").reset_index(drop=True)
        return df

    # ── status history builder ────────────────────────────────────────────────

    def build_status_history(
        self,
        scrip_master: pd.DataFrame,
        as_of_date: date | None = None,
    ) -> pd.DataFrame:
        """
        Build a per-scrip status snapshot from the current scrip master.

        Produces one row per scrip with its current status and the date
        it was observed. Used to populate fact_listing_status_history
        for BSE scrips when a full event log is not available.

        Args:
            scrip_master: dim_bse_scrip_master DataFrame
            as_of_date:   date to record as the observation date

        Returns:
            DataFrame with columns: scrip_code, status, effective_date
        """
        as_of_date = as_of_date or date.today()

        df = scrip_master[["scrip_code", "active_flag"]].copy()
        df["status"] = (
            df["active_flag"].map({True: "ACTIVE", False: "DELISTED"}).fillna("UNKNOWN")
        )
        df["effective_date"] = as_of_date.isoformat()

        return df[["scrip_code", "status", "effective_date"]].reset_index(drop=True)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_scrip_map(df: pd.DataFrame) -> dict[str, dict]:
        """Build code → row dict for fast lookup during comparison."""
        result: dict[str, dict] = {}
        for _, row in df.iterrows():
            code = str(row.get("scrip_code", "")).strip()
            if code:
                result[code] = row.to_dict()
        return result

    @staticmethod
    def _make_event(
        scrip_code: str,
        event_type: str,
        event_date: date,
        scrip_name_old: str | None = None,
        scrip_name_new: str | None = None,
        status_old: str | None = None,
        status_new: str | None = None,
        confidence: float = 0.5,
    ) -> dict:
        return {
            "scrip_code": scrip_code,
            "event_type": event_type,
            "effective_from": event_date.isoformat(),
            "effective_to": None,
            "scrip_name_old": scrip_name_old,
            "scrip_name_new": scrip_name_new,
            "status_old": status_old,
            "status_new": status_new,
            "confidence": confidence,
            "source": "bse_scrip_master_comparison",
        }
