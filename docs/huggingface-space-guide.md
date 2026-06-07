# HuggingFace Space: NSE India Security Master — Interactive Exploration Guide

This guide shows you how to use the TickerTruth NSE India Security Master dataset via the HuggingFace Space. Learn to query real corporate actions, explore symbol history, and apply results to your backtests and analyses.

---

## What You Can Explore

The Space gives you interactive access to four core datasets:

1. **Security Master** — Current and historical NSE equity symbols with metadata
2. **Corporate Actions** — Dividends, splits, bonuses, mergers, delistings with effective dates
3. **Symbol Lineage** — Ticker renames, mergers, status changes over time
4. **Adjustment Factors** — Pre-calculated ratios for price normalization

All data is versioned monthly. You can query specific dates or ranges, download results, and export to CSV/Parquet.

---

## Use Case 1: Fix a Broken Backtest with Split Adjustments

**Problem:** Your backtest shows an impossible price jump on a specific date. This usually means a stock split wasn't adjusted.

**Query:**
```sql
SELECT 
    symbol,
    ex_date,
    action_type,
    value_ratio,
    adjustment_factor
FROM fact_corporate_action_event
WHERE symbol = 'RELIANCE'
  AND action_type IN ('SPLIT', 'BONUS')
  AND ex_date BETWEEN '2020-01-01' AND '2026-06-07'
ORDER BY ex_date DESC;
```

**Example Result:**
```
symbol   | ex_date    | action_type | value_ratio | adjustment_factor
---------|------------|-------------|-------------|-------------------
RELIANCE | 2023-05-31 | SPLIT       | 1:5         | 0.2
RELIANCE | 2020-11-17 | BONUS       | 1:2         | 0.5
```

**How to Use It:**
- Find the split on **2023-05-31** with ratio **1:5** (means 1 new share for every 5 old shares)
- Adjustment factor **0.2** = multiply all prices BEFORE 2023-05-31 by 0.2 to make them comparable to post-split prices
- Example: If RELIANCE closed at ₹2000 on 2023-05-30, the adjusted price is `2000 × 0.2 = ₹400` (comparable to post-split prices)

**Apply to Backtest:**
```python
# Pseudo-code
historical_prices = load_prices(symbol='RELIANCE', start='2020-01-01', end='2026-06-07')
splits = query_splits(symbol='RELIANCE')

for split in splits:
    ex_date = split['ex_date']
    factor = split['adjustment_factor']
    # Adjust all prices BEFORE ex_date
    historical_prices[historical_prices.index < ex_date] *= factor

# Now your price series is continuous across splits
```

---

## Use Case 2: Reconcile a Portfolio NAV After Dividends

**Problem:** Your portfolio manager says the NAV dropped ₹50/share on a specific date, but prices didn't fall that much. What happened?

**Query:**
```sql
SELECT 
    symbol,
    ex_date,
    dividend_amount,
    COALESCE(frequency, 'INTERIM') as dividend_type
FROM fact_corporate_action_event
WHERE symbol IN ('INFY', 'TCS', 'WIPRO')
  AND action_type = 'DIVIDEND'
  AND ex_date = '2026-05-15'
ORDER BY symbol;
```

**Example Result:**
```
symbol | ex_date    | dividend_amount | dividend_type
-------|------------|-----------------|---------------
INFY   | 2026-05-15 | 21.0            | FINAL
TCS    | 2026-05-15 | 13.5            | INTERIM
WIPRO  | 2026-05-15 | 6.0             | FINAL
```

**How to Use It:**
- **INFY** went ex-dividend on **2026-05-15** paying **₹21/share**
- If a fund held 1000 INFY shares, it lost ₹21k in NAV due to the dividend (shareholders get cash, stock price drops by ~dividend amount)
- The portfolio manager would see a **₹21/share drop** in INFY on that date
- This is **expected** — it's the dividend payout, not a price decline

**Apply to Portfolio Analytics:**
```python
# Pseudo-code
portfolio = {'INFY': 1000_shares, 'TCS': 500_shares, 'WIPRO': 250_shares}
ex_dates = query_dividends(symbols=list(portfolio.keys()), date='2026-05-15')

dividend_impact = {}
for dividend in ex_dates:
    symbol = dividend['symbol']
    amount = dividend['dividend_amount']
    shares = portfolio[symbol]
    dividend_impact[symbol] = amount * shares

total_dividend = sum(dividend_impact.values())
# Portfolio NAV will drop by total_dividend, but it's cash outflow to shareholders (expected)
```

---

## Use Case 3: Track Symbol Renames for Data Pipeline Updates

**Problem:** Your production data pipeline has hardcoded symbol lists. When NSE renames a ticker, your pipeline breaks because it can't find price data under the old symbol.

**Query:**
```sql
SELECT 
    old_symbol,
    new_symbol,
    effective_date,
    reason
FROM lineage_symbol_event
WHERE event_type = 'RENAME'
  AND effective_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '24 months'
ORDER BY effective_date DESC;
```

**Example Result:**
```
old_symbol | new_symbol | effective_date | reason
-----------|------------|----------------|-------------------
POWERGRID  | POWERGRDL  | 2025-12-30     | Name change by issuer
AEGISLOG   | AEGIS      | 2025-10-15     | Name change by issuer
ORIENTCEM  | ORIENTCEM  | 2025-03-20     | Symbol optimization
```

**How to Use It:**
- **POWERGRID** became **POWERGRDL** on **2025-12-30**
- Historical price data exists under **POWERGRID** until that date, then under **POWERGRDL**
- Your pipeline should map both symbols to the same company for continuous backtesting

**Apply to Data Pipeline:**
```python
# Pseudo-code
symbol_map = build_symbol_map()  # {old_symbol: new_symbol, ...}

def get_price_series(security_id, start_date, end_date):
    # Get all symbol aliases for this security across the date range
    aliases = query_symbol_lineage(security_id=security_id, date_range=(start_date, end_date))
    
    prices = []
    for alias in aliases:
        symbol = alias['symbol']
        valid_from = alias['valid_from']
        valid_to = alias['valid_to']
        
        # Fetch prices for this symbol during its valid period
        data = fetch_prices(symbol=symbol, start=valid_from, end=valid_to)
        prices.append(data)
    
    # Concatenate and sort by date
    return pd.concat(prices).sort_index()
```

---

## Use Case 4: Understand Delisting Events and Merger Chains

**Problem:** A stock was delisted 5 years ago. Was it acquired? Renamed? Defaulted? You need the full history for research.

**Query:**
```sql
SELECT 
    symbol,
    event_type,
    effective_date,
    old_symbol,
    new_symbol,
    reason
FROM lineage_symbol_event
WHERE symbol IN ('ZENITHEQUIP', 'ADANIPORTS')  -- one active, one delisted/merged
ORDER BY effective_date DESC;
```

**Example Result:**
```
symbol       | event_type | effective_date | old_symbol    | new_symbol | reason
-------------|------------|----------------|---------------|------------|--------------------
ZENITHEQUIP  | DELISTING  | 2022-06-30     | ZENITHEQUIP   | NULL       | Merger with ICIL
ZENITHEQUIP  | MERGER     | 2022-06-30     | ZENITHEQUIP   | ICIL       | Reverse merger
ADANIPORTS   | ACTIVE     | NULL           | NULL          | NULL       | Currently trading
```

**How to Use It:**
- **ZENITHEQUIP** was **delisted** on **2022-06-30** due to a **merger with ICIL**
- Any backtest using ZENITHEQUIP data after this date is invalid — the company no longer trades
- If you want to include merged companies, you need to track **ICIL** (the surviving company) from that point forward
- For research, this explains why ZENITHEQUIP price data stops abruptly

**Apply to Research & Backtesting:**
```python
# Pseudo-code
def get_tradeable_symbols(as_of_date):
    """Get all symbols that were actively trading on this date"""
    return query_lineage(
        as_of_date=as_of_date,
        status='ACTIVE'  # excludes delisted, suspended, etc.
    )

def backtest_valid_period(symbol):
    """Returns (start_date, end_date) when symbol was tradeable"""
    history = query_symbol_lineage(symbol=symbol)
    start = history[0]['listing_date']
    end = history[-1]['delisting_date'] or CURRENT_DATE
    return (start, end)

# ZENITHEQUIP valid period: [inception, 2022-06-30)
# ADANIPORTS valid period: [inception, current] (still trading)
```

---

## Use Case 5: Validate Price Gaps Against Announced Events

**Problem:** You see a 15% price drop on a date. Is it a market crash or a dividend payment? Or a split adjustment?

**Query:**
```sql
SELECT 
    ca.symbol,
    ca.ex_date,
    ca.action_type,
    ca.value_ratio,
    bp.prev_close,
    bp.close,
    ((bp.close - bp.prev_close) / bp.prev_close * 100) as price_change_pct
FROM fact_corporate_action_event ca
LEFT JOIN fact_equity_eod bp ON ca.symbol = bp.symbol AND ca.ex_date = bp.date
WHERE ca.symbol = 'HCLTECH'
  AND ca.ex_date BETWEEN '2024-01-01' AND '2026-06-07'
ORDER BY ca.ex_date DESC;
```

**Example Result:**
```
symbol    | ex_date    | action_type | value_ratio | prev_close | close | price_change_pct
----------|------------|-------------|-------------|------------|-------|------------------
HCLTECH   | 2026-03-20 | DIVIDEND    | 15.0        | 1520.50    | 1505.15 | -1.0%
HCLTECH   | 2025-06-15 | SPLIT       | 1:5         | 1850.00    | 370.00  | -80.0%
HCLTECH   | 2024-08-10 | BONUS       | 1:1         | 1650.00    | 825.00  | -50.0%
```

**How to Use It:**
- **2025-06-15:** **1:5 split** → stock goes from ₹1850 to ₹370 (~80% drop). This is **expected**, not a crash.
- **2024-08-10:** **1:1 bonus** → stock goes from ₹1650 to ₹825 (~50% drop). This is **expected**, each share splits into 2.
- **2026-03-20:** **₹15 dividend** → stock drops ~1% (₹15 ÷ ₹1520 ≈ 1%). This is **expected**.

**How to Interpret:**
- If the price drop percentage matches the expected adjustment ratio, the event is **priced in**
- If the drop is much larger, there's additional market news (earnings miss, etc.)
- This helps you distinguish between **company-driven events** (corporate actions) and **market-driven events** (sentiment, macros)

---

## Use Case 6: Calculate Correct Adjustment Factors for Custom Analysis

**Problem:** You're building a custom price normalization and need to understand how to apply cascading adjustments (splits on top of bonuses, etc.).

**Query:**
```sql
SELECT 
    symbol,
    ex_date,
    action_type,
    value_ratio,
    adjustment_factor,
    cumulative_adjustment_factor
FROM fact_corporate_action_event
WHERE symbol = 'TATASTEEL'
ORDER BY ex_date ASC;
```

**Example Result:**
```
symbol    | ex_date    | action_type | value_ratio | adjustment_factor | cumulative_adjustment_factor
----------|------------|-------------|-------------|-------------------|-------------------------------
TATASTEEL | 2018-02-01 | BONUS       | 1:5         | 0.1667            | 0.1667
TATASTEEL | 2020-05-20 | SPLIT       | 1:2         | 0.5               | 0.0834
TATASTEEL | 2023-11-10 | DIVIDEND    | 15.0        | 1.0 (no split)    | 0.0834
```

**How to Use It:**
- **Cumulative adjustment** tells you how many new shares equal 1 original share
- **TATASTEEL 2018 holder:** 1 original share → 5 bonus shares (1:5 bonus) → 2.5 post-split shares → 2.5 current shares
- Cumulative factor = **0.0834** means 1 original share = 0.0834 current shares (or 1 current share = 12x original share)
- For a price from 2017, multiply by 0.0834 to make it comparable to 2024 prices

**Apply to Custom Normalization:**
```python
# Pseudo-code
def normalize_historical_price(symbol, price, price_date):
    """Convert a historical price to current-day comparable"""
    cumulative_factor = query_cumulative_adjustment(
        symbol=symbol,
        as_of_date=price_date
    )
    return price * cumulative_factor

# Example: TATASTEEL on 2017 at ₹100
# normalized = 100 * 0.0834 = ₹8.34 (comparable to 2024 prices)
```

---

## General Tips for Using the Space

### 1. **Always Filter by Date Range**
Corporate actions span decades. Without a date filter, queries are slow and results are overwhelming. Use `WHERE ex_date BETWEEN '2020-01-01' AND CURRENT_DATE` to stay focused.

### 2. **Use Symbol or ISIN for Precise Queries**
- Query by **symbol** for current events
- Query by **ISIN** for historical events (symbols change, ISINs don't)

### 3. **Understand Ex-Date vs. Payment Date**
- **Ex-Date:** First day you DON'T get the benefit (price drops ~dividend amount on this date)
- **Record Date:** Technical cutoff (you must own by this date to get the benefit)
- **Payment Date:** When you receive cash/shares
- For backtesting, use **ex-date**; for corporate records, use **record-date**

### 4. **Validate Against Price Movements**
Always cross-check corporate actions against actual bhavcopy price data. If a ₹20 dividend causes a 0.5% price drop instead of 1.5%, something else moved the market that day.

### 5. **Export and Transform Locally**
The Space is for exploration. For production, export results to CSV/Parquet and load into your backtest engine locally. Keep your own versioned copy of the mappings you use.

---

## What's NOT in This Dataset

- **Real-time feeds** — monthly snapshots only
- **BSE data** — NSE equities only (Phase 1)
- **Intraday data** — daily OHLCV only
- **Forecasts** — historical truth layer only
- **Fundamental data** — no earnings, PE, etc.

---

## Next Steps

1. **Explore the Space:** Run queries for your favorite stocks
2. **Test on Your Data:** Match our corporate action dates against your price data
3. **Integrate:** Use the mappings in your backtest pipeline
4. **Feedback:** Report discrepancies or missing events in the discussion thread

---

## Questions?

Ask in the [HuggingFace Discussion](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions) or check the [methodology docs](./methodology.md) for deeper technical details.
