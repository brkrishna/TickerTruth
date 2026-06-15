-- Core schema for India Symbol History and Corporate Actions Truth Layer
-- BSE extensions added in migration 002_bse_scrip_master.sql

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- Exchange dimension (NSE, BSE, etc.)
CREATE TABLE dim_exchange (
    exchange_id INT PRIMARY KEY,
    exchange_code VARCHAR(10) NOT NULL UNIQUE,
    exchange_name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Issuer/Company dimension
CREATE TABLE dim_issuer (
    issuer_id INT PRIMARY KEY AUTO_INCREMENT,
    issuer_name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    market_cap_category VARCHAR(50),
    country VARCHAR(50) NOT NULL DEFAULT 'India',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_issuer_name (issuer_name)
);

-- Security master dimension
CREATE TABLE dim_security_master (
    security_id INT PRIMARY KEY AUTO_INCREMENT,
    nse_symbol VARCHAR(50) NOT NULL UNIQUE,
    isin VARCHAR(12),
    company_name VARCHAR(255) NOT NULL,
    issuer_id INT NOT NULL,
    exchange_id INT NOT NULL,
    listing_date DATE,
    active_flag BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (issuer_id) REFERENCES dim_issuer(issuer_id),
    FOREIGN KEY (exchange_id) REFERENCES dim_exchange(exchange_id),
    KEY idx_nse_symbol (nse_symbol),
    KEY idx_isin (isin),
    KEY idx_active_flag (active_flag)
);

-- Symbol alias (historical symbol names for a security)
CREATE TABLE dim_symbol_alias (
    alias_id INT PRIMARY KEY AUTO_INCREMENT,
    security_id INT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    alias_type ENUM('current', 'historical', 'alternate') NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES dim_security_master(security_id),
    KEY idx_security_symbol (security_id, symbol),
    KEY idx_effective_dates (effective_from, effective_to)
);

-- Corporate action type lookup
CREATE TABLE dim_corporate_action_type (
    action_type_id INT PRIMARY KEY AUTO_INCREMENT,
    action_code VARCHAR(50) NOT NULL UNIQUE,
    action_name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- End-of-day equity price data
CREATE TABLE fact_equity_eod (
    eod_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    security_id INT NOT NULL,
    trading_date DATE NOT NULL,
    open_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    close_price DECIMAL(10, 2) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES dim_security_master(security_id),
    UNIQUE KEY uk_security_date (security_id, trading_date),
    KEY idx_trading_date (trading_date)
);

-- Corporate action events
CREATE TABLE fact_corporate_action_event (
    event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    security_id INT NOT NULL,
    action_type_id INT NOT NULL,
    event_date DATE NOT NULL,
    record_date DATE,
    payment_date DATE,
    old_value DECIMAL(15, 6),
    new_value DECIMAL(15, 6),
    adjustment_factor DECIMAL(15, 6),
    description TEXT,
    source VARCHAR(100),
    confidence_score DECIMAL(3, 2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES dim_security_master(security_id),
    FOREIGN KEY (action_type_id) REFERENCES dim_corporate_action_type(action_type_id),
    KEY idx_security_date (security_id, event_date),
    KEY idx_action_type (action_type_id)
);

-- Cumulative adjustment factors for backtesting
CREATE TABLE fact_adjustment_factor (
    adjustment_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    security_id INT NOT NULL,
    as_of_date DATE NOT NULL,
    cumulative_split_adjustment DECIMAL(15, 6) NOT NULL DEFAULT 1.0,
    cumulative_dividend_adjustment DECIMAL(15, 6) NOT NULL DEFAULT 1.0,
    cumulative_bonus_adjustment DECIMAL(15, 6) NOT NULL DEFAULT 1.0,
    total_adjustment_factor DECIMAL(15, 6) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES dim_security_master(security_id),
    UNIQUE KEY uk_security_asof (security_id, as_of_date),
    KEY idx_as_of_date (as_of_date)
);

-- Symbol and name lineage events
CREATE TABLE fact_symbol_lineage_event (
    lineage_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    security_id INT NOT NULL,
    old_symbol VARCHAR(50),
    new_symbol VARCHAR(50),
    change_date DATE NOT NULL,
    change_reason ENUM('rename', 'merger', 'split', 'delisting', 'relisting') NOT NULL,
    merged_with_symbol VARCHAR(50),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES dim_security_master(security_id),
    KEY idx_change_date (change_date),
    KEY idx_symbols (old_symbol, new_symbol)
);

-- Listing status history
CREATE TABLE fact_listing_status_history (
    status_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    security_id INT NOT NULL,
    status ENUM('active', 'suspended', 'delisted', 'relisted') NOT NULL,
    effective_date DATE NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (security_id) REFERENCES dim_security_master(security_id),
    KEY idx_security_date (security_id, effective_date),
    KEY idx_status (status)
);

-- ============================================================================
-- SAMPLE PUBLIC VIEWS
-- ============================================================================

-- Current active securities
CREATE VIEW vw_security_current AS
SELECT 
    sm.security_id,
    sm.nse_symbol,
    sm.isin,
    sm.company_name,
    di.issuer_name,
    di.sector,
    sm.listing_date,
    sm.active_flag
FROM dim_security_master sm
JOIN dim_issuer di ON sm.issuer_id = di.issuer_id
WHERE sm.active_flag = TRUE;

-- Symbol lineage sample (last 50 changes)
CREATE VIEW vw_symbol_lineage_sample AS
SELECT 
    sm.nse_symbol,
    fsl.old_symbol,
    fsl.new_symbol,
    fsl.change_date,
    fsl.change_reason,
    di.issuer_name
FROM fact_symbol_lineage_event fsl
JOIN dim_security_master sm ON fsl.security_id = sm.security_id
JOIN dim_issuer di ON sm.issuer_id = di.issuer_id
ORDER BY fsl.change_date DESC
LIMIT 50;

-- Corporate action timeline sample
CREATE VIEW vw_action_timeline_sample AS
SELECT 
    sm.nse_symbol,
    dcat.action_code,
    fca.event_date,
    fca.old_value,
    fca.new_value,
    fca.adjustment_factor,
    fca.confidence_score,
    di.issuer_name
FROM fact_corporate_action_event fca
JOIN dim_security_master sm ON fca.security_id = sm.security_id
JOIN dim_issuer di ON sm.issuer_id = di.issuer_id
JOIN dim_corporate_action_type dcat ON fca.action_type_id = dcat.action_type_id
ORDER BY fca.event_date DESC
LIMIT 100;

-- Adjusted price reference sample
CREATE VIEW vw_adjusted_price_reference_sample AS
SELECT 
    sm.nse_symbol,
    feo.trading_date,
    feo.close_price,
    faf.total_adjustment_factor,
    (feo.close_price / faf.total_adjustment_factor) AS adjusted_close_price,
    di.issuer_name
FROM fact_equity_eod feo
JOIN dim_security_master sm ON feo.security_id = sm.security_id
JOIN dim_issuer di ON sm.issuer_id = di.issuer_id
LEFT JOIN fact_adjustment_factor faf ON feo.security_id = faf.security_id 
    AND feo.trading_date >= faf.as_of_date
WHERE sm.nse_symbol IN (
    SELECT nse_symbol 
    FROM dim_security_master 
    LIMIT 20
)
ORDER BY sm.nse_symbol, feo.trading_date DESC
LIMIT 1000;