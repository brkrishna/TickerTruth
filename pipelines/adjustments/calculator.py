from datetime import date


class AdjustmentCalculator:
    def calculate_split_adjustment(old_numerator: int, new_denominator: int) -> float:
        # Return multiplier for adjusting historical prices
        pass
    
    def calculate_bonus_adjustment(bonus_ratio: float) -> float:
        # Calculate impact of bonus issue on historical prices
        pass
    
    def calculate_cumulative_adjustment(symbol: str, as_of_date: date) -> float:
        # Apply all adjustments from inception to as_of_date
        # Return cumulative multiplier
        pass