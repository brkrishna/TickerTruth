"""
Lineage detection rules for NSE symbol and company change events.

LineageEvent      — immutable value object for a single lineage event
LineageRulesEngine — detects renames, mergers, delistings, suspensions
"""

from datetime import date
from typing import Optional

from rapidfuzz import fuzz


# ── LineageEvent ──────────────────────────────────────────────────────────────


class LineageEvent:
    """
    Represents a significant event in a security's symbol or name history.

    Attributes:
        event_type (str): RENAME | MERGER | DEMERGER | DELISTING | RELISTING
                          | LISTING | SUSPENSION | REACTIVATION
        event_date (date): Date the event became effective
        symbol_from (str | None): Previous symbol; None for new listings
        symbol_to   (str | None): New symbol; None for delistings
        confidence  (float): 0.0 (guess) to 1.0 (certain)
        reason      (str): Human-readable explanation
        corroborating_evidence (list[str]): Supporting data points
    """

    VALID_TYPES = frozenset(
        {
            "RENAME",
            "MERGER",
            "DEMERGER",
            "DELISTING",
            "RELISTING",
            "LISTING",
            "SUSPENSION",
            "REACTIVATION",
        }
    )

    def __init__(
        self,
        event_type: str,
        event_date: date,
        confidence: float,
        symbol_from: Optional[str] = None,
        symbol_to: Optional[str] = None,
        reason: str = "",
        corroborating_evidence: Optional[list] = None,
    ):
        if event_type not in self.VALID_TYPES:
            raise ValueError(
                f"Unknown event_type '{event_type}'. Valid: {self.VALID_TYPES}"
            )
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {confidence}")

        self.event_type = event_type
        self.event_date = event_date
        self.confidence = round(confidence, 4)
        self.symbol_from = symbol_from
        self.symbol_to = symbol_to
        self.reason = reason
        self.corroborating_evidence = corroborating_evidence or []

    def __repr__(self) -> str:
        return (
            f"LineageEvent(type={self.event_type}, from={self.symbol_from}, "
            f"to={self.symbol_to}, date={self.event_date}, confidence={self.confidence})"
        )

    def to_dict(self) -> dict:
        """Serialize to a flat dict suitable for CSV / DataFrame row."""
        return {
            "symbol_from": self.symbol_from,
            "symbol_to": self.symbol_to,
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "corroborating_evidence": "; ".join(self.corroborating_evidence),
        }


# ── LineageRulesEngine ────────────────────────────────────────────────────────


class LineageRulesEngine:
    """
    Detects and classifies symbol lineage events from raw NSE data.

    Each method is a pure detector — it takes raw inputs and returns
    a LineageEvent (or tuple with confidence) without side effects.
    """

    # ── renames ───────────────────────────────────────────────────────────────

    def detect_symbol_rename(
        self,
        prev_symbol: str,
        new_symbol: str,
        event_date: date,
        company_name: Optional[str] = None,
        new_company_name: Optional[str] = None,
    ) -> LineageEvent:
        """
        Detect a ticker symbol rename for the same issuer.

        Confidence rules:
          - 0.95 if company_name matches new_company_name (same entity confirmed)
          - 0.85 if one company name provided (partial confirmation)
          - 0.75 if no company names provided (symbol change, entity unverified)

        Returns:
            LineageEvent(type=RENAME, symbol_from=prev_symbol, symbol_to=new_symbol)
        """
        if prev_symbol == new_symbol:
            raise ValueError(
                f"prev_symbol and new_symbol are identical ({prev_symbol!r}); "
                "no rename to detect"
            )

        evidence = []

        if company_name and new_company_name:
            sim = fuzz.ratio(company_name.upper(), new_company_name.upper()) / 100
            if sim >= 0.85:
                confidence = 0.95
                evidence.append(f"company_name_similarity={sim:.2f}")
            else:
                # Names diverged — lower confidence; might be merger disguised as rename
                confidence = 0.70
                evidence.append(
                    f"company_name_similarity={sim:.2f} (names differ — may be merger)"
                )
        elif company_name or new_company_name:
            confidence = 0.85
            evidence.append("single_company_name_provided")
        else:
            confidence = 0.75
            evidence.append("no_company_name_context")

        return LineageEvent(
            event_type="RENAME",
            event_date=event_date,
            confidence=confidence,
            symbol_from=prev_symbol,
            symbol_to=new_symbol,
            reason=f"Symbol changed from {prev_symbol} to {new_symbol}",
            corroborating_evidence=evidence,
        )

    def detect_company_rename(
        self,
        prev_name: str,
        new_name: str,
        event_date: date,
        fuzzy_threshold: float = 0.85,
    ) -> tuple[Optional[LineageEvent], float]:
        """
        Use fuzzy name matching to detect a company rename.

        Args:
            prev_name: Previous company legal name
            new_name:  New company legal name
            event_date: Date the rename became effective
            fuzzy_threshold: Minimum similarity score to flag as rename (0–1)

        Returns:
            (LineageEvent, similarity_score) if rename detected,
            (None, similarity_score) otherwise.
        """
        if not prev_name or not new_name:
            return None, 0.0

        similarity = fuzz.ratio(prev_name.upper(), new_name.upper()) / 100

        if similarity < fuzzy_threshold:
            return None, similarity

        event = LineageEvent(
            event_type="RENAME",
            event_date=event_date,
            confidence=round(similarity, 4),
            reason=f"Company name changed: {prev_name!r} → {new_name!r}",
            corroborating_evidence=[f"fuzzy_similarity={similarity:.2f}"],
        )
        return event, similarity

    # ── mergers / demergers ───────────────────────────────────────────────────

    def detect_merger_demerger(
        self,
        symbol_disappears: bool,
        new_symbol_appears: bool,
        old_symbol: str,
        new_symbol: str,
        event_date: date,
        corporate_action: Optional[dict] = None,
    ) -> LineageEvent:
        """
        Detect merger or demerger events.

        Classification logic:
          - MERGER  if old symbol disappears (absorbed into another entity)
          - DEMERGER if old symbol persists and a new one appears alongside

        Confidence rules:
          - 0.95 if corporate_action confirms MERGER/DEMERGER
          - 0.75 if symbol disappears without corroborating action
          - 0.60 if ambiguous (no disappearance, no action)

        Returns:
            LineageEvent(type=MERGER | DEMERGER)
        """
        evidence = []
        event_type = "MERGER" if symbol_disappears else "DEMERGER"

        if corporate_action:
            ca_type = str(corporate_action.get("action_code", "")).upper()
            if ca_type in ("MERGER", "DEMERGER", "AMALGAMATION"):
                confidence = 0.95
                evidence.append(f"corporate_action={ca_type}")
                if ca_type == "DEMERGER":
                    event_type = "DEMERGER"
            else:
                confidence = 0.70
                evidence.append(f"corporate_action={ca_type} (not a merger type)")
        elif symbol_disappears:
            confidence = 0.75
            evidence.append("symbol_disappeared_no_corroborating_action")
        else:
            confidence = 0.60
            evidence.append("inferred_from_symbol_overlap_only")

        if new_symbol_appears:
            evidence.append(f"new_symbol_appeared={new_symbol}")

        return LineageEvent(
            event_type=event_type,
            event_date=event_date,
            confidence=confidence,
            symbol_from=old_symbol,
            symbol_to=new_symbol if new_symbol != old_symbol else None,
            reason=f"{event_type}: {old_symbol} → {new_symbol}",
            corroborating_evidence=evidence,
        )

    # ── delistings ────────────────────────────────────────────────────────────

    def detect_delisting(
        self,
        symbol: str,
        last_trading_date: date,
        is_explicit: bool = False,
    ) -> LineageEvent:
        """
        Detect when a symbol stops appearing in the active trading list.

        Args:
            symbol:            Trading symbol being delisted
            last_trading_date: Last date the symbol appeared in active data
            is_explicit:       True if NSE published a formal delisting notice

        Returns:
            LineageEvent(type=DELISTING, symbol_from=symbol)
        """
        confidence = 0.95 if is_explicit else 0.75
        reason = (
            f"Explicit NSE delisting notice for {symbol}"
            if is_explicit
            else f"{symbol} absent from active list after {last_trading_date}"
        )
        evidence = ["explicit_nse_notice"] if is_explicit else ["inferred_from_absence"]

        return LineageEvent(
            event_type="DELISTING",
            event_date=last_trading_date,
            confidence=confidence,
            symbol_from=symbol,
            symbol_to=None,
            reason=reason,
            corroborating_evidence=evidence,
        )

    # ── relistings ────────────────────────────────────────────────────────────

    def detect_relisting(
        self,
        symbol: str,
        relisting_date: date,
        reason: str = "",
    ) -> LineageEvent:
        """
        Detect when a previously delisted symbol resumes trading.

        Returns:
            LineageEvent(type=RELISTING, symbol_to=symbol)
        """
        return LineageEvent(
            event_type="RELISTING",
            event_date=relisting_date,
            confidence=0.90,
            symbol_from=None,
            symbol_to=symbol,
            reason=reason or f"{symbol} relisted on NSE",
            corroborating_evidence=["symbol_reappeared_in_active_list"],
        )

    # ── suspensions ───────────────────────────────────────────────────────────

    def detect_suspension(
        self,
        symbol: str,
        suspension_date: date,
        reason: str = "",
    ) -> LineageEvent:
        """
        Detect a temporary trading suspension.

        Returns:
            LineageEvent(type=SUSPENSION, symbol_from=symbol)
        """
        return LineageEvent(
            event_type="SUSPENSION",
            event_date=suspension_date,
            confidence=0.90,
            symbol_from=symbol,
            symbol_to=None,
            reason=reason or f"{symbol} suspended from trading",
            corroborating_evidence=["symbol_in_suspended_status"],
        )
