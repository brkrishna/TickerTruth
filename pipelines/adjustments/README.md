# Adjustments Pipeline

## Responsibility

Compute cumulative adjustment factors (split ratios, dividend yields, bonus factors) for each security to enable price series normalization for backtesting. This layer processes corporate action events and builds the `fact_adjustment_factor` table with pre-computed adjustments.

## Inputs

- Corporate action events from `data/staging/corporate_actions_{YYYYMMDD}.parquet`
- Curated security master from `data/curated/dim_security_master/`
- EOD price data from `data/staging/nse_eod_{YYYYMMDD}.parquet`
- Existing adjustment factors from Dolt (for incremental updates)

## Outputs

- **Curated Facts**:
  - `data/curated/fact_adjustment_factor/` (cumulative adjustments per security, date)
- **Reference**:
  - `data/curated/fact_corporate_action_event/` (detailed event records)
- **Diagnostics**:
  - `data/staging/adjustments_report.md` (summary of factors by security)
  - `data/staging/adjustment_conflicts.csv` (overlapping corporate actions, timing issues)

## Adjustment Types

### 1. Stock Splits
**Adjustment Factor = new_ratio / old_ratio** (e.g., 1:2 split → 2.0)
- Forward adjustment: multiply historical prices by factor to normalize to current (to calculate adjusted close = close / factor)
- Example: 2:1 split on 2020-06-15; factor = 2.0
  - Prices before 2020-06-15: divide by 2.0 to adjust to current basis
  - Prices after: use as-is (current basis)

### 2. Bonuses
**Adjustment Factor = (old_shares + new_shares) / old_shares** (e.g., 1:1 bonus → 2.0)
- 1:1 bonus: shareholder gets 1 free share per existing share (doubles shares, halves price)
- 2:1 bonus: 2 free shares per existing share (triples shares, price / 3)

### 3. Dividends
**Adjustment Factor ≈ 1.0 - (dividend_per_share / close_price_on_ex_date)**
- Dividend reduces shareholder wealth, reflected in price drop on ex-date
- Example: ₹50 dividend on ₹1000 close → adjustment = 1000 / (1000 - 50) = 1.050
- Cumulative dividend adjustment tracks total wealth erosion over time

### 4. Rights Issues
**Adjustment Factor = (old_value_per_share + subscription_cost_per_share) / old_value_per_share**
- Dilutive event; shareholders can subscribe at preferential rate
- Example: 1:4 rights at ₹100 on ₹500 stock → factor = (500 + 125) / 500 = 1.25

### 5. Demergers & Reorganizations
**Adjustment Factor = complex; requires special handling**
- Demerger: one company splits into two; shareholders get shares in both
- Factor = (value_old_company + value_spun_off) / value_old_company
- Often requires manual calibration; tagged with lower confidence

## Computation Algorithm

```
FOR EACH SECURITY:
  1. Retrieve all corporate actions (sorted by event_date ascending)
  2. Start with cumulative_factor = 1.0 as of listing_date
  3. FOR EACH ACTION (chronologically):
     a. Compute adjustment_factor based on action type & parameters
     b. cumulative_factor *= adjustment_factor
     c. Create fact_adjustment_factor record (as_of_action_date, cumulative)
  4. Back-fill missing dates (holidays, suspended days) with last known factor
  5. Output cumulative adjustment for every trading date in dataset
```

## Expected Artifacts

```
pipelines/adjustments/
├── __init__.py
├── README.md                          # This file
├── adjustment_calculator.py           # Core computation engine
├── split_calculator.py                # Stock split logic
├── dividend_calculator.py             # Dividend adjustment logic
├── bonus_calculator.py                # Bonus issue logic
├── rights_calculator.py               # Rights issue logic
├── demerger_calculator.py             # Complex reorganization logic
├── conflict_detector.py               # Overlapping action detection
├── config.yaml                        # Thresholds, special cases
├── special_cases/
│   ├── known_issues.yaml              # Manually verified adjustments
│   ├── demerger_mappings.yaml         # Custom demerger factors
│   └── rights_details.yaml            # Rights issue specifics
├── requirements.txt                   # Dependencies (pandas, numpy)
└── tests/
    ├── test_split_calculator.py
    ├── test_dividend_calculator.py
    ├── test_cumulative_factors.py
    ├── fixtures/
    │   ├── sample_corporate_actions.csv
    │   └── expected_adjustments.parquet
    └── integration/
        └── test_price_normalization.py
```

## Data Quality Issues & Resolution

| Issue | Resolution |
|-------|-----------|
| Duplicate corporate actions (same action announced twice) | Keep most recent official announcement; log duplicate |
| Overlapping actions (split + bonus same day) | Treat as simultaneous; multiply factors |
| Missing ex-date (only payment date available) | Infer ex-date = record_date - 1 day; flag with confidence <0.95 |
| Action effective date in future | Skip for now; apply on event date during next pipeline run |
| Very small dividend (< ₹0.01) | Likely data entry error; review manually |
| Action amount 10x expected (₹100 dividend on ₹10 stock) | Likely data error; flag for review; estimate correction |
| Stock split with fractional ratio (1:1.5) | Handle; compute ratio accurately |

## Validation Rules

1. **Temporal Consistency**
   - No adjustment factors retroactively modified (immutable once created)
   - adjustment_factor > 0 always
   - cumulative_factor generally 0.1 to 10.0 (flag if outside range)

2. **Price Reconciliation (Optional)**
   - For each corporate action, validate price behavior on ex-date
   - Split: expect price drop of ~1/split_ratio
   - Dividend: expect price drop of ~dividend / previous_close
   - Flag if actual price movement significantly deviates (>20% error)

3. **Cross-Checks**
   - Verify adjustment factor matches dividend/split announcements
   - Compare to third-party sources (if available) for large-cap stocks
   - Flag significant discrepancies for manual review

## Output Specifications

### fact_adjustment_factor
```
adjustment_id | security_id | as_of_date | cumulative_split_adjustment | cumulative_dividend_adjustment | cumulative_bonus_adjustment | total_adjustment_factor
1             | 1           | 1999-06-11 | 1.0                         | 1.0                            | 1.0                         | 1.0
2             | 1           | 2000-03-15 | 2.0                         | 1.0                            | 1.0                         | 2.0  (2:1 split)
3             | 1           | 2001-08-22 | 2.0                         | 0.95                           | 1.0                         | 1.90 (₹50 dividend)
4             | 1           | 2005-06-30 | 2.0                         | 0.92                           | 3.0                         | 5.52 (3:1 bonus)
```

### fact_corporate_action_event
```
event_id | security_id | action_type_id | event_date  | record_date | payment_date | old_value | new_value | adjustment_factor | description | confidence_score
100      | 1           | 3 (SPLIT)      | 2000-03-15  | NULL        | NULL         | 1         | 2         | 2.0               | 2:1 split   | 0.99
101      | 1           | 1 (DIVIDEND)   | 2001-08-22  | 2001-08-25  | 2001-09-15   | 50        | NULL      | 0.95              | Interim div | 0.98
```

## SLA & Monitoring

- **Completion Time**: <5 minutes for all securities combined
- **Data Quality**: Minimum 0.85 confidence_score per adjustment
- **Coverage**: 100% of corporate actions with valid security_id
- **Validation**: No NULL adjustment_factors for trading dates

## Next Steps

Output from this pipeline → **publish/** pipeline (export samples and prepare for distribution)
