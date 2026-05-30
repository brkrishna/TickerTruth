import datetime


class FieldNormalizer:
    def normalize_ticker(symbol: str) -> str:
        pass

    def normalize_company_name(name: str) -> str:
        pass

    def normalize_date(date_str: str) -> datetime.date:
        pass

    def normalize_action_type(action: str) -> str:
        pass

    def normalize_numeric(value: str) -> float:
        pass