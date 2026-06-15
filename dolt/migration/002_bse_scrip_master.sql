-- Migration: 002_bse_scrip_master
-- Author: RA
-- Date: 2026-06-15
-- Purpose: Add BSE scrip master, scrip lineage, and cross-exchange ISIN bridge tables
-- Breaking: no (additive only)
-- Rollback: DROP TABLE dim_bse_scrip_master, fact_bse_scrip_lineage_event, fact_exchange_security_map

-- BSE dimension: one row per scrip code (BSE's numeric security identifier)
CREATE TABLE IF NOT EXISTS dim_bse_scrip_master (
    scrip_id        INT PRIMARY KEY AUTO_INCREMENT,
    scrip_code      VARCHAR(10) NOT NULL,   -- e.g. "500325" for Reliance
    isin            VARCHAR(12),
    scrip_name      VARCHAR(255) NOT NULL,  -- short name (≤12 chars)
    company_name    VARCHAR(255),           -- full registered name
    segment         VARCHAR(20),            -- EQ / SME / MF / etc.
    issuer_id       INT,                    -- FK → dim_issuer (resolved post-normalize)
    listing_date    DATE,
    active_flag     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_scrip_code (scrip_code),
    KEY idx_isin (isin),
    KEY idx_active (active_flag),
    FOREIGN KEY (issuer_id) REFERENCES dim_issuer(issuer_id)
);

-- BSE scrip lineage: per-scrip timeline of name, status, and code changes
CREATE TABLE IF NOT EXISTS fact_bse_scrip_lineage_event (
    lineage_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
    scrip_id        INT NOT NULL,
    event_type      ENUM(
                        'RENAME','STATUS_CHANGE','CODE_REASSIGN',
                        'DELISTING','RELISTING','LISTING'
                    ) NOT NULL,
    effective_from  DATE NOT NULL,
    effective_to    DATE,                   -- NULL means still current
    scrip_name_old  VARCHAR(255),
    scrip_name_new  VARCHAR(255),
    status_old      VARCHAR(50),
    status_new      VARCHAR(50),
    confidence      DECIMAL(3,2),
    source          VARCHAR(100),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_scrip_date (scrip_id, effective_from),
    FOREIGN KEY (scrip_id) REFERENCES dim_bse_scrip_master(scrip_id)
);

-- Cross-exchange ISIN bridge: dual-listed and BSE-only universe
-- One row per ISIN; NULL on nse_symbol means BSE-only listing.
CREATE TABLE IF NOT EXISTS fact_exchange_security_map (
    map_id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    isin                VARCHAR(12) NOT NULL,
    nse_symbol          VARCHAR(50),            -- NULL for BSE-only
    nse_effective_from  DATE,
    nse_effective_to    DATE,
    bse_scrip_code      VARCHAR(10),            -- NULL for NSE-only
    bse_effective_from  DATE,
    bse_effective_to    DATE,
    is_bse_only         BOOLEAN NOT NULL DEFAULT FALSE,
    is_nse_only         BOOLEAN NOT NULL DEFAULT FALSE,
    ca_date_conflict    BOOLEAN NOT NULL DEFAULT FALSE, -- NSE/BSE action date mismatch
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_isin (isin),
    KEY idx_nse_symbol (nse_symbol),
    KEY idx_bse_scrip (bse_scrip_code)
);
