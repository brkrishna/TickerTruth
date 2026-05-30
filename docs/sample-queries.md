# Sample SQL Queries

These queries work on the core fact and dimension tables once loaded into Dolt or a SQL engine.

## Query 1: Find all splits for a ticker

```sql
SELECT 
    symbol,
    event_date,
    old_shares,
    new_shares,
    adjustment_factor
FROM fact_corporate_action_event
JOIN dim_symbol_alias ON fact_corporate_action_event.security_id = dim_symbol_alias.security_id
WHERE action_type = 'SPLIT'
  AND symbol = 'RELIANCE'
ORDER BY event_date DESC;
```

## Query 2: Get dividend-adjusted price series

```sql
SELECT 
    lineage_date,
    symbol,
    close_price,
    close_price / COALESCE(SUM(cumulative_dividend_adjustment), 1.0) OVER (
        PARTITION BY symbol ORDER BY lineage_date
    ) AS adjusted_close
FROM fact_equity_eod
JOIN dim_symbol_alias ON fact_equity_eod.security_id = dim_symbol_alias.security_id
WHERE symbol = 'INFY'
ORDER BY lineage_date;
```

## Query 3: Track symbol name changes over time

```sql
SELECT 
    security_id,
    old_symbol,
    new_symbol,
    change_date,
    change_reason
FROM fact_symbol_lineage_event
WHERE security_id IN (SELECT security_id FROM dim_security_master WHERE issuer_name LIKE '%Tech%')
ORDER BY change_date DESC;
```

## Query 4: Identify broken backtests due to missing adjustments

```sql
SELECT 
    symbol,
    COUNT(*) as missing_adjustments
FROM fact_corporate_action_event
WHERE security_id NOT IN (SELECT security_id FROM fact_adjustment_factor)
  AND action_type IN ('SPLIT', 'BONUS', 'DIVIDEND')
GROUP BY symbol
HAVING COUNT(*) > 0;
```
