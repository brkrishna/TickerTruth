import pandas as pd


class AdjustmentValidator:
    def validate_against_lineage(
        adjustments: pd.DataFrame, lineage: pd.DataFrame
    ) -> pd.DataFrame:
        # For each adjustment, check:
        # - Symbol exists in dim_security_master on event_date
        # - Symbol hasn't been delisted before event_date
        # - No conflicting lineage events on same date
        # Flag mismatches for review
        pass

    def validate_against_price_gaps(
        adjustments: pd.DataFrame, eod_prices: pd.DataFrame
    ) -> pd.DataFrame:
        # For stock splits/bonus, check if historical price gap matches expected adjustment
        # Example: If 1:2 split, expect price to ~2x on ex_date
        # Flag unexplained gaps
        pass

    def detect_overlapping_adjustments(adjustments: pd.DataFrame) -> list:
        # Warn if multiple adjustments apply to same date
        # This can cause double-counting in cumulative factors
        pass
