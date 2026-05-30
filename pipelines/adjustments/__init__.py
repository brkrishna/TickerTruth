"""Adjustments Pipeline

Computes cumulative adjustment factors (split ratios, dividend yields, bonus factors) for each security.
Enables price series normalization for accurate backtesting.

Module structure:
- adjustment_calculator.py: Core computation engine
- split_calculator.py: Stock split adjustment logic
- dividend_calculator.py: Dividend adjustment logic
- bonus_calculator.py: Bonus issue adjustment logic
- demerger_calculator.py: Complex reorganization handling

See README.md for detailed responsibilities and implementation notes.
"""

__version__ = "1.0.0"
