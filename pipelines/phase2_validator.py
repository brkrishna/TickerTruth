class Phase2Validator:
    def validate_extraction(self):
        # Raw files exist, have content, no corruption
        # Dates are fresh
        pass

    def validate_normalization(self):
        # Mapped schemas match expected columns
        # No required field is completely missing
        # Primary keys are unique
        # Referential integrity: all security_ids exist in dim_security
        pass
    
    def validate_lineage():
        # No circular symbol chains
        # Delisting dates make sense (after listing)
        # Lineage events are chronologically ordered per symbol
        # Confidence scores are assigned
        pass
    
    def validate_adjustments():
        # All corporate action types are recognized
        # Factors are reasonable (split > 0, bonus > 1)
        # Cumulative factors are monotonic or explained
        # No gaps in backtest-critical symbols
        pass
    
    def cross_validate_all():
        # Symbol in adjustment exists in lineage exists in security_master
        # Action event dates ≥ listing date and ≤ delisting date (if any)
        # Merger lineage matches merger corporate action events
        # No symbol appears in multiple lineage paths (except delisting→relisting)
        pass