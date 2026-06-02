"""
Adjustment factor calculations for corporate action events.

Implements the formulas from adjustments/rules.yaml.
All methods are static — pure math, no I/O or state.
"""

import pandas as pd


class AdjustmentCalculator:
    """
    Computes price adjustment factors for individual and cumulative corporate actions.

    Formula reference (from rules.yaml):
        split:  factor = old_shares / new_shares
        bonus:  factor = existing / (existing + bonus)

    A factor < 1 means historical prices should be multiplied DOWN to match
    the post-action price level (prices fell after the split/bonus).

    Usage:
        AdjustmentCalculator.calculate_split_adjustment(1, 2)   # 1:2 split → 0.5
        AdjustmentCalculator.calculate_bonus_adjustment(1, 1)   # 1:1 bonus → 0.5
    """

    @staticmethod
    def calculate_split_adjustment(
        old_numerator: int | float, new_denominator: int | float
    ) -> float:
        """
        Compute the price adjustment factor for a stock split.

        Formula: factor = old_shares / new_shares
        A 1:2 split (one share becomes two) gives factor = 0.5.
        Multiply historical prices by this factor to get adjusted prices.

        Args:
            old_numerator:   Shares before split (the '1' in 1:2)
            new_denominator: Shares after split  (the '2' in 1:2)

        Returns:
            float factor in (0, 1] for a normal split; > 1 for a reverse split.

        Raises:
            ValueError if either argument is ≤ 0.
        """
        if old_numerator <= 0 or new_denominator <= 0:
            raise ValueError(
                f"Split ratio values must be positive; got {old_numerator}:{new_denominator}"
            )
        return float(old_numerator) / float(new_denominator)

    @staticmethod
    def calculate_bonus_adjustment(
        existing_shares: int | float, bonus_shares: int | float
    ) -> float:
        """
        Compute the price adjustment factor for a bonus (stock dividend) issue.

        Formula: factor = existing / (existing + bonus)
        A 1:1 bonus (one bonus share per existing share) gives factor = 0.5.

        Args:
            existing_shares: Shares held before bonus (the '1' in '1 for 1')
            bonus_shares:    Bonus shares issued per existing share

        Returns:
            float factor in (0, 1).

        Raises:
            ValueError if either argument is ≤ 0.
        """
        if existing_shares <= 0 or bonus_shares <= 0:
            raise ValueError(
                f"Bonus ratio values must be positive; got {existing_shares}:{bonus_shares}"
            )
        return float(existing_shares) / float(existing_shares + bonus_shares)

    @staticmethod
    def calculate_cumulative_adjustment(
        action_events: pd.DataFrame,
    ) -> dict[str, float]:
        """
        Compute cumulative split, bonus, and total adjustment factors from a
        sequence of corporate action events for a single security.

        Events are applied chronologically (earliest first). Each action
        multiplies the running factor for its type.

        Args:
            action_events: DataFrame with columns action_code and old_value,
                           sorted ascending by event_date. Typically a subset
                           of fact_corporate_action_event for one security.

        Returns:
            dict with keys:
              cumulative_split_adjustment  — product of all split factors
              cumulative_bonus_adjustment  — product of all bonus factors
              total_adjustment_factor      — split × bonus combined

        Raises:
            ValueError if action_events contains rows with zero/negative values
            that would make the factor invalid.
        """
        split_factor = 1.0
        bonus_factor = 1.0

        for _, row in action_events.iterrows():
            code = str(row.get("action_code", "")).upper().strip()
            value = row.get("old_value")

            if code == "SPLIT":
                # old_value stored as old:new ratio by normalizer (e.g. 0.5 for 1:2)
                # If ratio already computed (< 1), use directly; otherwise treat as denominator
                if value is not None and not pd.isna(value):
                    ratio = float(value)
                    if ratio <= 0:
                        raise ValueError(
                            f"Invalid split factor {ratio} for row {dict(row)}"
                        )
                    split_factor *= ratio

            elif code == "BONUS":
                # old_value stored as old:new ratio by normalizer (e.g. 0.5 for 1:1 bonus)
                if value is not None and not pd.isna(value):
                    ratio = float(value)
                    if ratio <= 0:
                        raise ValueError(
                            f"Invalid bonus factor {ratio} for row {dict(row)}"
                        )
                    bonus_factor *= ratio

            elif code == "REVERSE_SPLIT":
                # Reverse split: factor > 1 (prices go up)
                if value is not None and not pd.isna(value):
                    ratio = float(value)
                    if ratio <= 0:
                        raise ValueError(
                            f"Invalid reverse split factor {ratio} for row {dict(row)}"
                        )
                    split_factor *= ratio

        total = round(split_factor * bonus_factor, 8)
        return {
            "cumulative_split_adjustment": round(split_factor, 8),
            "cumulative_bonus_adjustment": round(bonus_factor, 8),
            "total_adjustment_factor": total,
        }
