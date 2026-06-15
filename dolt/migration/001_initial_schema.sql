-- Migration: 001_initial_schema
-- Author: RA
-- Date: 2026-06-01
-- Purpose: Initial NSE schema (extracted from schema.sql baseline)
-- Breaking: no
-- Rollback: drop_tables.sql

-- NSE exchange_id = 1, BSE exchange_id = 2 (reserved; see 002_bse_scrip_master.sql)
INSERT IGNORE INTO dim_exchange (exchange_id, exchange_code, exchange_name, country)
VALUES
  (1, 'NSE', 'National Stock Exchange of India', 'India'),
  (2, 'BSE', 'BSE Limited (Bombay Stock Exchange)', 'India');
