-- ICASHTL Sample Queries
-- Compatible with: Dolt (MySQL), Snowflake, BigQuery, DuckDB

-- 1. All active securities
SELECT nse_symbol, isin, company_name, sector, listing_date
FROM dim_security_master
WHERE active_flag = TRUE
ORDER BY listing_date DESC;

-- 2. Corporate actions for a symbol
SELECT action_code, event_date, old_value, confidence_score
FROM fact_corporate_action_event
WHERE security_id = (
    SELECT security_id FROM dim_security_master WHERE nse_symbol = 'INFY'
)
ORDER BY event_date DESC;

-- 3. Backtest-adjusted price calculation
SELECT
    e.trading_date,
    e.close_price,
    f.total_adjustment_factor,
    e.close_price * f.total_adjustment_factor AS adjusted_close
FROM fact_equity_eod e
JOIN fact_adjustment_factor f
  ON e.security_id = f.security_id
 AND e.trading_date >= f.as_of_date
WHERE e.security_id = (
    SELECT security_id FROM dim_security_master WHERE nse_symbol = 'RELIANCE'
)
ORDER BY e.trading_date;
