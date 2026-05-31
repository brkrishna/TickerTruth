"""
Raw data extractor for NSE equity master, corporate actions, and bhavcopy.

Step 5a: fetch_nse_symbols()           — NSE equity master CSV (implemented)
Step 5b: fetch_bhavcopy()              — NSE daily EOD zip (stub)
Step 5c: fetch_nse_corporate_actions() — NSE corporate actions via Playwright (stub)
Step 5d: consolidate_to_staging()      — merge daily raw files to staging (stub)
"""

import json
import logging
import time
from datetime import date
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"

NSE_BASE = "https://www.nseindia.com"

# NSE serves equity master as JSON via its internal API.
# The cookie handshake (hitting the home page first) is required —
# NSE blocks direct API calls without a valid session cookie.
NSE_EQUITY_MASTER_API = "https://www.nseindia.com/api/equity-master"

# Fallback: older direct CSV URL (still works on some NSE mirrors)
NSE_EQUITY_CSV_FALLBACK = "https://www.nseindia.com/content/equities/EQUITY_L.csv"

# Minimum expected row count for a valid equity master file
MIN_SYMBOL_ROWS = 3500

# Required columns (after normalization) for validation
REQUIRED_SYMBOL_COLUMNS = ["SYMBOL", "ISIN", "LISTING_DATE", "STATUS"]

# Browser-like headers — NSE rejects requests without these
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

# NSE column name aliases across different file format versions
_COLUMN_ALIASES = {
    "NAME OF COMPANY": "COMPANY_NAME",
    "NAME_OF_COMPANY": "COMPANY_NAME",
    "NAME": "COMPANY_NAME",
    "ISIN NUMBER": "ISIN",
    "ISIN_NUMBER": "ISIN",
    "ISIN NO": "ISIN",
    "DATE OF LISTING": "LISTING_DATE",
    "DATE_OF_LISTING": "LISTING_DATE",
    "TRADING STATUS": "STATUS",
    "TRADING_STATUS": "STATUS",
    "INDUSTRY": "SECTOR",
    "INDUSTRY_NAME": "SECTOR",
    "SERIES": "SERIES",
}


# ── extractor ────────────────────────────────────────────────────────────────

class RawDataExtractor:
    """
    Downloads raw source files from NSE and saves them to data/raw/.

    Usage:
        extractor = RawDataExtractor()
        df = extractor.fetch_nse_symbols()
    """

    def __init__(self, output_dir: Path = DATA_RAW):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session: requests.Session | None = None

    # ── session management ───────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        """
        Return a requests.Session with NSE session cookies set.

        NSE blocks API calls without a prior homepage visit that sets
        cookies (nseappid, ak_bmsc, etc.). This method handles that handshake.
        """
        if self._session is not None:
            return self._session

        session = requests.Session()
        session.headers.update(_BROWSER_HEADERS)

        logger.info("Performing NSE cookie handshake...")
        try:
            # Step 1: hit the homepage to receive session cookies
            resp = session.get(NSE_BASE, timeout=15)
            resp.raise_for_status()
            logger.info("Cookie handshake succeeded (HTTP %s)", resp.status_code)
        except requests.RequestException as exc:
            logger.warning("Cookie handshake failed: %s — continuing anyway", exc)

        # Brief pause to avoid triggering NSE rate limiting
        time.sleep(1.5)
        self._session = session
        return session

    # ── step 5a: NSE equity master ───────────────────────────────────────────

    def fetch_nse_symbols(self) -> pd.DataFrame:
        """
        Download the NSE equity master and return a cleaned DataFrame.

        Tries the JSON API endpoint first, falls back to the legacy CSV URL.
        Saves the raw file to data/raw/nse_symbols_{YYYY-MM-DD}.csv.

        Returns:
            DataFrame with columns including SYMBOL, COMPANY_NAME, ISIN,
            LISTING_DATE, STATUS, SECTOR, SERIES.

        Raises:
            RuntimeError: if both URLs fail or the file is empty.
            ValueError: if required columns are missing or row count is too low.
        """
        today = date.today().isoformat()
        out_path = self.output_dir / f"nse_symbols_{today}.csv"

        # Skip network call if today's file already exists (idempotent)
        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Using cached file: %s", out_path)
            return pd.read_csv(out_path)

        session = self._get_session()
        df = self._fetch_equity_master_json(session)

        if df is None:
            logger.warning("JSON API failed, trying legacy CSV URL...")
            df = self._fetch_equity_master_csv(session)

        if df is None or df.empty:
            raise RuntimeError(
                "Failed to fetch NSE equity master from all URLs. "
                "Check your network connection or NSE site status."
            )

        df = self._normalize_symbol_columns(df)
        self._validate_symbols(df)

        df.to_csv(out_path, index=False)
        logger.info("Saved %d symbols → %s", len(df), out_path)
        return df

    def _fetch_equity_master_json(self, session: requests.Session) -> pd.DataFrame | None:
        """Try the NSE JSON API endpoint."""
        try:
            resp = session.get(
                NSE_EQUITY_MASTER_API,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            # The API returns a list of dicts or a dict with a data key
            if isinstance(data, list):
                return pd.DataFrame(data)
            if isinstance(data, dict):
                # Try common wrapper keys
                for key in ("data", "records", "equities"):
                    if key in data:
                        return pd.DataFrame(data[key])
                # No known wrapper — return flat dict as single row (unlikely)
                return pd.DataFrame([data])

        except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
            logger.warning("JSON API call failed: %s", exc)
            return None

    def _fetch_equity_master_csv(self, session: requests.Session) -> pd.DataFrame | None:
        """Try the legacy direct CSV download URL."""
        try:
            resp = session.get(NSE_EQUITY_CSV_FALLBACK, timeout=30)
            resp.raise_for_status()
            # Detect if response is actually HTML (redirect to login page)
            if resp.text.strip().startswith("<"):
                logger.warning("CSV URL returned HTML — NSE may have changed the endpoint")
                return None
            return pd.read_csv(StringIO(resp.text))
        except Exception as exc:
            logger.warning("CSV fallback failed: %s", exc)
            return None

    def _normalize_symbol_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names across different NSE file format versions.
        Strips whitespace, uppercases, and applies known aliases.
        """
        # Strip whitespace from column names and uppercase
        df.columns = [c.strip().upper() for c in df.columns]

        # Apply aliases (handles both space-separated and underscore variants)
        rename_map = {k: v for k, v in _COLUMN_ALIASES.items() if k in df.columns}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Deduplicate on [SYMBOL, LISTING_DATE] — keep last (most recent)
        dedup_cols = [c for c in ["SYMBOL", "LISTING_DATE"] if c in df.columns]
        if dedup_cols:
            before = len(df)
            df.drop_duplicates(subset=dedup_cols, keep="last", inplace=True)
            dropped = before - len(df)
            if dropped:
                logger.warning("Dropped %d duplicate (SYMBOL, LISTING_DATE) rows", dropped)

        return df.reset_index(drop=True)

    def _validate_symbols(self, df: pd.DataFrame) -> None:
        """
        Validate the equity master DataFrame before saving.
        Raises ValueError on hard failures; logs warnings for soft issues.
        """
        # Hard check: required columns must exist
        missing = [c for c in REQUIRED_SYMBOL_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"NSE equity master is missing required columns: {missing}. "
                f"Columns present: {list(df.columns)}"
            )

        # Hard check: minimum row count
        if len(df) < MIN_SYMBOL_ROWS:
            raise ValueError(
                f"NSE equity master has only {len(df)} rows — expected ≥ {MIN_SYMBOL_ROWS}. "
                "The download may be incomplete or the URL may have changed."
            )

        # Soft checks: log warnings but do not raise
        null_isin = df["ISIN"].isna().sum()
        if null_isin:
            logger.warning("%d rows have a missing ISIN", null_isin)

        null_listing = df["LISTING_DATE"].isna().sum()
        if null_listing:
            logger.warning("%d rows have a missing LISTING_DATE", null_listing)

        logger.info(
            "Validation passed: %d symbols, %d missing ISIN, %d missing LISTING_DATE",
            len(df), null_isin, null_listing,
        )

    # ── step 5b stub ─────────────────────────────────────────────────────────

    def fetch_bhavcopy(self, trading_date: date) -> pd.DataFrame:
        """Download NSE daily EOD bhavcopy zip for a given trading date."""
        raise NotImplementedError(f"Step 5b — implement fetch_bhavcopy() for {trading_date}")

    # ── step 5c stub ─────────────────────────────────────────────────────────

    def fetch_nse_corporate_actions(self) -> pd.DataFrame:
        """Scrape NSE corporate actions page using Playwright."""
        raise NotImplementedError("Step 5c — implement fetch_nse_corporate_actions()")

    # ── step 5d stub ─────────────────────────────────────────────────────────

    def consolidate_to_staging(self) -> None:
        """Merge all daily raw files in data/raw/ into consolidated staging files."""
        raise NotImplementedError("Step 5d — implement consolidate_to_staging()")