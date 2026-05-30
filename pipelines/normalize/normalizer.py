import pandas as pd


class RawToCanonicalMapper:
    def map_to_dim_security_master(raw_symbols: pd.DataFrame) -> pd.DataFrame:
        # Map: symbol, isin, name, sector, listing_date → canonical dim schema
        # Output columns: security_id, ticker, isin, name, sector, 
        #                listing_date, delisting_date, status
        pass
    
    def map_to_dim_issuer(raw_issuers: pd.DataFrame) -> pd.DataFrame:
        # Map issuer/company fields → canonical issuer dimension
        pass

    def map_to_fact_corporate_action_event(raw_actions: pd.DataFrame) -> pd.DataFrame:
        # Map: symbol, ex_date, action_type, value → canonical fact schema
        # Output: action_id, security_id, action_type, ex_date, record_date,
        #         payment_date, value, unit, qdivisor, qdividend
        pass