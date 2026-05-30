-- Drop views first
DROP VIEW IF EXISTS vw_adjusted_price_reference_sample;
DROP VIEW IF EXISTS vw_action_timeline_sample;
DROP VIEW IF EXISTS vw_symbol_lineage_sample;
DROP VIEW IF EXISTS vw_security_current;

-- Drop fact tables (no FK dependencies between them)
DROP TABLE IF EXISTS fact_listing_status_history;
DROP TABLE IF EXISTS fact_symbol_lineage_event;
DROP TABLE IF EXISTS fact_adjustment_factor;
DROP TABLE IF EXISTS fact_corporate_action_event;
DROP TABLE IF EXISTS fact_equity_eod;

-- Drop dimension tables (drop in reverse dependency order)
DROP TABLE IF EXISTS dim_symbol_alias;
DROP TABLE IF EXISTS dim_security_master;
DROP TABLE IF EXISTS dim_corporate_action_type;
DROP TABLE IF EXISTS dim_issuer;
DROP TABLE IF EXISTS dim_exchange;