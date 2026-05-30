import pandas as pd


class RawDataExtractor:
    def fetch_nse_symbols() -> pd.DataFrame:
        # Fetch current/historical symbol list
        # Return: DataFrame with [symbol, name, isin, listing_date, status, ...]
        pass
    
    def fetch_nse_corporate_actions() -> pd.DataFrame:
        # Fetch corporate action announcements
        # Return: DataFrame with [symbol, ex_date, action_type, value, ...]
        pass
    
    def fetch_issuer_details() -> pd.DataFrame:
        # Fetch issuer/company master info
        # Return: DataFrame with [isin, company_name, sector, ...]
        pass