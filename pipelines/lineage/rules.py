from datetime import date
from typing import List, Optional


class LineageEvent:
    """
    Represents a significant event in a security's symbol or name history.
    
    Attributes:
        symbol_from (str): Previous symbol (None for new listings)
        symbol_to (str): New symbol (None for delistings)
        event_date (date): Date the event became effective
        event_type (str): Type of event (RENAME, SPLIT, MERGER, DELISTING, LISTING, SUSPENSION, REACTIVATION)
        confidence (float): Confidence score (0.0 to 1.0)
        reason (str): Human-readable explanation
        corroborating_evidence (List[str]): Supporting evidence for the event
    """
    
    def __init__(
        self,
        event_type: str,
        event_date: date,
        confidence: float,
        symbol_from: Optional[str] = None,
        symbol_to: Optional[str] = None,
        reason: str = "",
        corroborating_evidence: Optional[List[str]] = None
    ):
        self.symbol_from = symbol_from
        self.symbol_to = symbol_to
        self.event_date = event_date
        self.event_type = event_type
        self.confidence = confidence
        self.reason = reason
        self.corroborating_evidence = corroborating_evidence or []
    
    def __repr__(self) -> str:
        return (
            f"LineageEvent(type={self.event_type}, from={self.symbol_from}, "
            f"to={self.symbol_to}, date={self.event_date}, confidence={self.confidence})"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            "symbol_from": self.symbol_from,
            "symbol_to": self.symbol_to,
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "corroborating_evidence": "; ".join(self.corroborating_evidence),
        }


class LineageRulesEngine:
    """
    Engine for detecting and classifying symbol lineage events.
    
    Processes historical symbol lists, corporate actions, and circulars
    to identify symbol renames, mergers, delistings, and other lineage events.
    """
    
    def detect_symbol_rename(
        self, 
        prev_symbol: str, 
        new_symbol: str, 
        event_date: date,
        company_name: Optional[str] = None,
        new_company_name: Optional[str] = None
    ) -> LineageEvent:
        """
        Detect if symbol changed but issuer remained the same.
        
        Args:
            prev_symbol: Previous trading symbol
            new_symbol: New trading symbol
            event_date: Date the rename became effective
            company_name: Previous company name (optional, for validation)
            new_company_name: New company name (optional, for validation)
        
        Returns:
            LineageEvent with type=RENAME if rename detected
        """
        # Detect if symbol changed but issuer is same
        # Output: LineageEvent(type=RENAME, from_symbol, to_symbol, effective_date)
        pass

    def detect_company_rename(
        self, 
        prev_name: str, 
        new_name: str, 
        event_date: date,
        fuzzy_threshold: float = 0.85
    ) -> tuple[Optional[LineageEvent], float]:
        """
        Use fuzzy name matching to detect company renames.
        
        Args:
            prev_name: Previous company legal name
            new_name: New company legal name
            event_date: Date the rename became effective
            fuzzy_threshold: Minimum similarity score (0.0-1.0) to flag as rename
        
        Returns:
            Tuple of (LineageEvent if rename detected, confidence score)
        """
        # Use fuzzy name matching to detect renames
        # Return: LineageEvent and confidence score
        pass
    
    def detect_merger_demerger(
        self, 
        symbol_disappears: bool, 
        new_symbol_appears: bool,
        old_symbol: str,
        new_symbol: str,
        event_date: date,
        corporate_action: Optional[dict] = None
    ) -> LineageEvent:
        """
        Detect merger or demerger events.
        
        Args:
            symbol_disappears: Whether old symbol stops trading
            new_symbol_appears: Whether new symbol starts trading
            old_symbol: Symbol that disappeared
            new_symbol: Symbol that appeared (may be same as old if demerger)
            event_date: Date of the merger/demerger
            corporate_action: Corporate action event dict for corroboration
        
        Returns:
            LineageEvent with type=MERGER or DEMERGER
        """
        # Cross-reference with corporate action events
        # Output: LineageEvent(type=MERGER or DEMERGER, from_symbol, to_symbol, date)
        pass
    
    def detect_delisting(
        self, 
        symbol: str, 
        last_trading_date: date,
        is_explicit: bool = False
    ) -> LineageEvent:
        """
        Detect when symbol stops appearing in active list (delisting).
        
        Args:
            symbol: Trading symbol being delisted
            last_trading_date: Last date symbol appeared in active trading list
            is_explicit: Whether delisting was explicitly announced (vs. inferred)
        
        Returns:
            LineageEvent with type=DELISTING
        """
        # Detect when symbol stops appearing in active list
        # Output: LineageEvent(type=DELISTING, symbol, delisting_date)
        pass
    
    def detect_relisting(
        self,
        symbol: str,
        relisting_date: date,
        reason: str = ""
    ) -> LineageEvent:
        """
        Detect when a previously delisted symbol returns to trading.
        
        Args:
            symbol: Trading symbol being relisted
            relisting_date: Date symbol resumes trading
            reason: Reason for relisting (e.g., "reopened_after_suspension")
        
        Returns:
            LineageEvent with type=RELISTING
        """
        # Detect reactivation of previously delisted symbol
        pass
    
    def detect_suspension(
        self,
        symbol: str,
        suspension_date: date,
        reason: str = ""
    ) -> LineageEvent:
        """
        Detect temporary trading suspension.
        
        Args:
            symbol: Trading symbol being suspended
            suspension_date: Date suspension began
            reason: Reason for suspension
        
        Returns:
            LineageEvent with type=SUSPENSION
        """
        # Detect temporary suspension events
        pass