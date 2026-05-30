import pandas as pd


class AdjustmentFactorBuilder:
    def build_from_corporate_actions(actions: pd.DataFrame,
                                    symbols: pd.DataFrame) -> pd.DataFrame:
        # Input: fact_corporate_action_event (from normalization)
        # For each action:
        #   - Identify action type (split, bonus, etc.)
        #   - Extract numerator/denominator or ratio
        #   - Calculate multiplier using rules
        #   - Validate against historical price series (if available)
        # Output: fact_adjustment_factor rows
        pass