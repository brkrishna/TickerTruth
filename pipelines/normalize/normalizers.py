"""
Field-level normalizers for raw NSE data.

All methods are static — no state, no side effects.
Each takes a single raw value and returns a canonical Python type.
"""

import re
import unicodedata
from datetime import date, datetime


# ── action type mapping ───────────────────────────────────────────────────────
# Maps raw NSE subject/purpose strings (lowercase) → canonical action codes.
# Canonical codes match dim_corporate_action_type.action_code in schema.sql.

_ACTION_TYPE_MAP: dict[str, str] = {
    # Dividends
    "dividend":                      "DIVIDEND",
    "cash dividend":                  "DIVIDEND",
    "interim dividend":               "DIVIDEND",
    "final dividend":                 "DIVIDEND",
    "special dividend":               "SPECIAL_DIVIDEND",
    "preference dividend":            "PREFERENCE_DIVIDEND",
    "dividend reinvestment":          "DIVIDEND_REINVESTMENT",
    # Bonus
    "bonus":                          "BONUS",
    "bonus issue":                    "BONUS",
    "bonus shares":                   "BONUS",
    # Splits
    "split":                          "SPLIT",
    "stock split":                    "SPLIT",
    "sub-division":                   "SPLIT",
    "subdivision":                    "SPLIT",
    "face value split":               "SPLIT",
    "reverse split":                  "REVERSE_SPLIT",
    "consolidation":                  "REVERSE_SPLIT",
    "reverse stock split":            "REVERSE_SPLIT",
    # Rights
    "rights":                         "RIGHTS",
    "rights issue":                   "RIGHTS",
    "rights offering":                "RIGHTS",
    # Mergers / demergers
    "merger":                         "MERGER",
    "amalgamation":                   "MERGER",
    "merger/amalgamation":            "MERGER",
    "acquisition":                    "MERGER",
    "demerger":                       "DEMERGER",
    "spin-off":                       "DEMERGER",
    "spinoff":                        "DEMERGER",
    "demerger/spinoff":               "DEMERGER",
    # Listing events
    "ipo":                            "LISTING",
    "listing":                        "LISTING",
    "relisting":                      "RELISTING",
    "delisting":                      "DELISTING",
    "voluntary delisting":            "DELISTING",
    "compulsory delisting":           "DELISTING",
    # Capital events
    "capital reduction":              "CAPITAL_REDUCTION",
    "buyback":                        "CAPITAL_REDUCTION",
    "buy back":                       "CAPITAL_REDUCTION",
    "capital increase":               "CAPITAL_INCREASE",
    "further public offer":           "CAPITAL_INCREASE",
    "fpo":                            "CAPITAL_INCREASE",
    # Name / symbol changes
    "name change":                    "NAME_CHANGE",
    "symbol change":                  "NAME_CHANGE",
    "namechange":                     "NAME_CHANGE",
}

# Date formats NSE uses across different data sources
_DATE_FORMATS: list[str] = [
    "%d-%m-%Y",    # 28-05-2024  (most NSE CSVs)
    "%d/%m/%Y",    # 28/05/2024
    "%Y-%m-%d",    # 2024-05-28  (ISO, used in some API responses)
    "%d-%b-%Y",    # 28-May-2024 (bhavcopy TIMESTAMP)
    "%d-%B-%Y",    # 28-May-2024 full month name
    "%b %d, %Y",   # May 28, 2024
    "%d %b %Y",    # 28 May 2024
]

# Suffixes NSE appends to equity symbols — stripped during normalization
_SYMBOL_SUFFIX_RE = re.compile(
    r"-(EQ|REPL|BE|BL|IL|SM|N[1-9]|GR|BZ|BT|MF|GB|GS|SG|TB|EQ1)$",
    re.IGNORECASE,
)

# Company name variants to normalise
_COMPANY_NAME_SUBS: list[tuple[re.Pattern, str]] = [
    # Punctuation and spacing
    (re.compile(r"\s+"),                       " "),             # collapse whitespace
    (re.compile(r"[&]"),                       "AND"),           # & → AND
    # Legal suffix variants — use lookahead (?=\s|,|$) instead of \b
    # because \b does not match after a period at end-of-string
    (re.compile(r"\bLTD\.?(?=\s|,|$)",  re.I), "LIMITED"),
    (re.compile(r"\bPVT\.?(?=\s|,|$)",  re.I), "PRIVATE"),
    (re.compile(r"\bCO\.?(?=\s|,|$)",   re.I), "COMPANY"),
    (re.compile(r"\bCORP\.?(?=\s|,|$)", re.I), "CORPORATION"),
    (re.compile(r"\bINC\.?(?=\s|,|$)",  re.I), "INCORPORATED"),
    (re.compile(r"\bINTL\.?(?=\s|,|$)", re.I), "INTERNATIONAL"),
    (re.compile(r"\bINDS\.?(?=\s|,|$)", re.I), "INDUSTRIES"),
    (re.compile(r"\bMFG\.?(?=\s|,|$)",  re.I), "MANUFACTURING"),
]

# Currency / unit symbols to strip when normalising numerics
_CURRENCY_RE = re.compile(r"[₹$€£¥]|Rs\.?\s*|INR\s*|USD\s*", re.IGNORECASE)


# ── normalizer class ──────────────────────────────────────────────────────────

class FieldNormalizer:
    """
    Pure static methods for field-level normalization of NSE raw data.

    Usage:
        from pipelines.normalize.normalizers import FieldNormalizer as FN
        FN.normalize_ticker("INFY-EQ")         # → "INFY"
        FN.normalize_date("28-05-2024")        # → date(2024, 5, 28)
        FN.normalize_action_type("Bonus Issue") # → "BONUS"
    """

    @staticmethod
    def normalize_ticker(symbol: str) -> str:
        """
        Clean an NSE trading symbol to its canonical form.

        Strips whitespace, uppercases, and removes exchange/series suffixes
        (e.g. -EQ, -REPL, -BE) that NSE appends in some data files.

        Returns empty string if input is None or blank.
        """
        if not symbol or not isinstance(symbol, str):
            return ""
        ticker = symbol.strip().upper()
        ticker = _SYMBOL_SUFFIX_RE.sub("", ticker)
        return ticker.strip()

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """
        Standardise a company name to a canonical uppercase form.

        - Removes leading/trailing whitespace
        - Collapses internal spaces
        - Replaces non-ASCII characters with ASCII equivalents where possible
        - Normalises legal suffix variants (Ltd → LIMITED, Pvt → PRIVATE, etc.)

        Returns empty string if input is None or blank.
        """
        if not name or not isinstance(name, str):
            return ""

        # Normalise unicode → ASCII where possible (handles curly quotes, etc.)
        name = unicodedata.normalize("NFKD", name)
        name = name.encode("ascii", errors="ignore").decode("ascii")

        name = name.strip().upper()

        for pattern, replacement in _COMPANY_NAME_SUBS:
            name = pattern.sub(replacement, name)

        return name.strip()

    @staticmethod
    def normalize_date(date_str: str) -> date | None:
        """
        Parse a date string using all known NSE date formats.

        Tries formats in order: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD,
        DD-MMM-YYYY (e.g. 28-May-2024), and several others.

        Returns:
            datetime.date on success, None if no format matches or input is blank.
        """
        if not date_str or not isinstance(date_str, str):
            return None

        cleaned = date_str.strip()
        if not cleaned or cleaned.upper() in ("-", "NA", "N/A", "NULL", "NONE", "NIL"):
            return None

        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue

        return None  # caller should log this as a quality issue

    @staticmethod
    def normalize_action_type(action: str) -> str:
        """
        Map a raw NSE corporate action description to a canonical action code.

        Matching is case-insensitive and strips punctuation before lookup.
        Returns "UNKNOWN" if no mapping is found — callers should flag this
        for manual review.
        """
        if not action or not isinstance(action, str):
            return "UNKNOWN"

        key = action.strip().lower()
        # Direct lookup
        if key in _ACTION_TYPE_MAP:
            return _ACTION_TYPE_MAP[key]

        # Partial / prefix match — handles "Interim Dividend - Rs.5.00" etc.
        for raw_key, canonical in _ACTION_TYPE_MAP.items():
            if raw_key in key or key.startswith(raw_key):
                return canonical

        return "UNKNOWN"

    @staticmethod
    def normalize_numeric(value: str | float | int) -> float | None:
        """
        Parse a numeric value from NSE data, stripping currency symbols,
        commas, and unit labels.

        Handles:
        - "₹5.00", "Rs.5.00", "INR 5"  → 5.0
        - "1,00,000" (Indian comma format) → 100000.0
        - "1:2" (ratio) → 0.5  (old:new, so factor = 1/2)
        - "10%" → 0.1
        - None, "", "N/A" → None

        Returns:
            float on success, None if the value cannot be parsed.
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        if not cleaned or cleaned.upper() in ("NA", "N/A", "NULL", "NIL", "-", ""):
            return None

        # Strip currency symbols and labels
        cleaned = _CURRENCY_RE.sub("", cleaned).strip()

        # Handle ratio notation "old:new" → factor (old/new)
        if ":" in cleaned:
            parts = cleaned.split(":")
            try:
                numerator   = float(parts[0].replace(",", ""))
                denominator = float(parts[1].replace(",", ""))
                return numerator / denominator if denominator else None
            except (ValueError, IndexError):
                return None

        # Handle percentage
        if cleaned.endswith("%"):
            try:
                return float(cleaned[:-1].replace(",", "")) / 100
            except ValueError:
                return None

        # Strip commas (Indian number format: 1,00,000)
        cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return None
