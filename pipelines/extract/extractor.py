"""
Raw data extractor for NSE equity master, corporate actions, and bhavcopy.

Step 5a: fetch_nse_symbols()           — NSE equity master CSV (implemented)
Step 5b: fetch_bhavcopy()              — NSE daily EOD zip (implemented)
Step 5c: fetch_nse_corporate_actions() — NSE corporate actions (implemented)
Step 5d: consolidate_to_staging()      — merge daily raw files to staging (stub)
"""

import json
import logging
import time
from datetime import date, timedelta
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

# Corporate actions JSON API — requires a valid NSE session cookie
NSE_CORP_ACTIONS_API = (
    "https://www.nseindia.com/api/corporates-corporateActions"
)

# Corporate actions page for Playwright fallback
NSE_CORP_ACTIONS_PAGE = (
    "https://www.nseindia.com/companies-listing/corporate-filings-actions"
)

# NSE API returns at most ~30 days of records per call; chunk longer ranges
CORP_ACTIONS_CHUNK_DAYS = 30

# Default lookback when no date range is specified
CORP_ACTIONS_DEFAULT_LOOKBACK_DAYS = 90

# Map NSE API field names → our canonical column names
_CORP_ACTION_API_COLUMNS = {
    "symbol":   "SYMBOL",
    "series":   "SERIES",
    "subject":  "ACTION_TYPE_RAW",
    "exDate":   "EX_DATE",
    "recDate":  "RECORD_DATE",
    "payDate":  "PAYMENT_DATE",
    "comp":     "COMPANY_NAME",
    "faceVal":  "FACE_VALUE",
    "bcStDate": "BC_START_DATE",
    "bcEndDate":"BC_END_DATE",
}

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

    # ── step 5b: NSE bhavcopy ────────────────────────────────────────────────

    def fetch_bhavcopy(self, trading_date: date) -> pd.DataFrame:
        """
        Download NSE equity bhavcopy (EOD market data) for a given trading date.

        NSE publishes a ZIP file after market close (~6 PM IST) containing a CSV
        with OHLCV data for all traded securities.

        URL pattern:
            https://archives.nseindia.com/content/historical/EQUITIES/
            {YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip

        Args:
            trading_date: The trading date to fetch. Must be a weekday when
                          markets were open — NSE does not publish bhavcopy
                          for holidays or weekends.

        Returns:
            DataFrame with columns: SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE,
            LAST, PREVCLOSE, TOTTRDQTY, TOTTRDVAL, TIMESTAMP, TOTALTRADES, ISIN.

        Raises:
            RuntimeError: if the download fails (e.g. holiday, network error).
            ValueError: if required columns are missing or OHLC sanity fails.
        """
        out_path = self.output_dir / f"bhavcopy_{trading_date.isoformat()}.csv"

        # Skip download if file already exists (idempotent)
        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Using cached bhavcopy: %s", out_path)
            return pd.read_csv(out_path)

        url = self._bhavcopy_url(trading_date)
        logger.info("Downloading bhavcopy from %s", url)

        session = self._get_session()
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                raise RuntimeError(
                    f"Bhavcopy not found for {trading_date} (HTTP 404). "
                    "Likely a market holiday, weekend, or the file is not yet published."
                ) from exc
            raise RuntimeError(f"Failed to download bhavcopy for {trading_date}: {exc}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to download bhavcopy for {trading_date}: {exc}") from exc

        df = self._extract_bhavcopy_zip(resp.content, trading_date)
        df = self._normalize_bhavcopy_columns(df)
        self._validate_bhavcopy(df, trading_date)

        df.to_csv(out_path, index=False)
        logger.info("Saved %d rows bhavcopy → %s", len(df), out_path)
        return df

    def _bhavcopy_url(self, trading_date: date) -> str:
        """Build the NSE archives URL for a given trading date."""
        yyyy = trading_date.strftime("%Y")
        mmm = trading_date.strftime("%b").upper()   # e.g. MAY, JAN
        dd = trading_date.strftime("%d")             # zero-padded day
        filename = f"cm{dd}{mmm}{yyyy}bhav.csv.zip"
        return (
            f"https://archives.nseindia.com/content/historical/"
            f"EQUITIES/{yyyy}/{mmm}/{filename}"
        )

    def _extract_bhavcopy_zip(self, content: bytes, trading_date: date) -> pd.DataFrame:
        """Extract the CSV from the downloaded ZIP bytes and parse into DataFrame."""
        import zipfile
        from io import BytesIO

        try:
            zf = zipfile.ZipFile(BytesIO(content))
        except zipfile.BadZipFile as exc:
            raise RuntimeError(
                f"Downloaded file for {trading_date} is not a valid ZIP. "
                "NSE may have returned an error page instead."
            ) from exc

        csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_files:
            raise RuntimeError(
                f"No CSV found inside bhavcopy ZIP for {trading_date}. "
                f"ZIP contents: {zf.namelist()}"
            )

        # Prefer the equity bhavcopy file (cm*.csv) over any other CSV in the zip
        csv_name = next(
            (n for n in csv_files if n.upper().startswith("CM")),
            csv_files[0],
        )
        logger.info("Extracting %s from ZIP", csv_name)
        return pd.read_csv(zf.open(csv_name))

    def _normalize_bhavcopy_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Uppercase and strip all column names; rename legacy header variants."""
        df.columns = [c.strip().upper() for c in df.columns]

        # Handle older bhavcopy formats that used different column names
        bhavcopy_aliases = {
            "TOTTRDQTY": "TOTTRDQTY",   # already standard
            "VOLUME": "TOTTRDQTY",
            "TOTTRDVAL": "TOTTRDVAL",
            "VALUE": "TOTTRDVAL",
            "TOTALTRADES": "TOTALTRADES",
            "NO_OF_TRADES": "TOTALTRADES",
        }
        rename_map = {k: v for k, v in bhavcopy_aliases.items() if k in df.columns and k != v}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        return df.reset_index(drop=True)

    def _validate_bhavcopy(self, df: pd.DataFrame, trading_date: date) -> None:
        """
        Validate bhavcopy DataFrame before saving.
        Hard failures raise ValueError; soft issues log warnings.
        """
        required = ["SYMBOL", "OPEN", "HIGH", "LOW", "CLOSE"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Bhavcopy for {trading_date} missing required columns: {missing}. "
                f"Columns present: {list(df.columns)}"
            )

        # Minimum row count — a normal trading day has ~2000+ EQ series rows
        min_rows = 500
        if len(df) < min_rows:
            raise ValueError(
                f"Bhavcopy for {trading_date} has only {len(df)} rows — "
                f"expected ≥ {min_rows}. File may be incomplete."
            )

        # OHLC sanity: LOW <= CLOSE <= HIGH (allow tiny float drift)
        eq = df[df.get("SERIES", pd.Series(["EQ"] * len(df))) == "EQ"] if "SERIES" in df.columns else df
        ohlc_ok = (
            (eq["LOW"] <= eq["CLOSE"] + 0.01) &
            (eq["CLOSE"] <= eq["HIGH"] + 0.01)
        )
        bad_ohlc = (~ohlc_ok).sum()
        if bad_ohlc > 0:
            logger.warning(
                "%d rows in bhavcopy for %s fail OHLC sanity (LOW > CLOSE or CLOSE > HIGH)",
                bad_ohlc, trading_date,
            )

        # Warn on zero-volume rows (suspended/delisted securities)
        if "TOTTRDQTY" in df.columns:
            zero_vol = (df["TOTTRDQTY"] == 0).sum()
            if zero_vol:
                logger.warning(
                    "%d rows have zero volume in bhavcopy for %s "
                    "(may indicate suspended or delisted securities)",
                    zero_vol, trading_date,
                )

        logger.info(
            "Bhavcopy validation passed: %d rows, date=%s",
            len(df), trading_date,
        )

    # ── step 5c: NSE corporate actions ──────────────────────────────────────

    def fetch_nse_corporate_actions(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> pd.DataFrame:
        """
        Fetch NSE corporate action announcements for a date range.

        Tries the NSE JSON API first (fast, no browser). Falls back to
        Playwright scraping if the API is blocked or returns no data.

        NSE limits API responses to ~30 days per call. Longer ranges are
        automatically split into monthly chunks and concatenated.

        Args:
            from_date: Start of date range (inclusive). Defaults to
                       CORP_ACTIONS_DEFAULT_LOOKBACK_DAYS days ago.
            to_date:   End of date range (inclusive). Defaults to today.

        Returns:
            DataFrame with columns: SYMBOL, SERIES, ACTION_TYPE_RAW,
            EX_DATE, RECORD_DATE, PAYMENT_DATE, COMPANY_NAME, FACE_VALUE.

        Raises:
            RuntimeError: if both the API and Playwright fallback fail.
        """
        to_date = to_date or date.today()
        from_date = from_date or (to_date - timedelta(days=CORP_ACTIONS_DEFAULT_LOOKBACK_DAYS))

        out_path = self.output_dir / (
            f"nse_actions_{from_date.isoformat()}_{to_date.isoformat()}.csv"
        )

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Using cached corporate actions: %s", out_path)
            return pd.read_csv(out_path)

        # Try JSON API first — split into monthly chunks
        session = self._get_session()
        chunks = list(self._date_chunks(from_date, to_date, CORP_ACTIONS_CHUNK_DAYS))
        logger.info(
            "Fetching corporate actions %s → %s in %d chunk(s)",
            from_date, to_date, len(chunks),
        )

        all_frames: list[pd.DataFrame] = []
        api_failed = False

        for chunk_from, chunk_to in chunks:
            df = self._fetch_corp_actions_api(session, chunk_from, chunk_to)
            if df is None:
                logger.warning(
                    "JSON API failed for chunk %s → %s", chunk_from, chunk_to
                )
                api_failed = True
                break
            if not df.empty:
                all_frames.append(df)
            time.sleep(1.5)   # rate limit between chunk calls

        if api_failed or not all_frames:
            logger.warning("Falling back to Playwright for corporate actions")
            fallback_df = self._fetch_corp_actions_playwright(from_date, to_date)
            if fallback_df is None or fallback_df.empty:
                raise RuntimeError(
                    f"Failed to fetch corporate actions {from_date} → {to_date} "
                    "from both JSON API and Playwright."
                )
            all_frames = [fallback_df]

        df = pd.concat(all_frames, ignore_index=True)
        df = self._normalize_corp_actions_columns(df)
        df.drop_duplicates(
            subset=["SYMBOL", "EX_DATE", "ACTION_TYPE_RAW"], keep="last", inplace=True
        )
        self._validate_corp_actions(df)

        df.to_csv(out_path, index=False)
        logger.info("Saved %d corporate action rows → %s", len(df), out_path)
        return df

    # ── corp actions helpers ─────────────────────────────────────────────────

    @staticmethod
    def _date_chunks(
        from_date: date, to_date: date, chunk_days: int
    ):
        """Yield (chunk_from, chunk_to) pairs covering [from_date, to_date]."""
        cursor = from_date
        while cursor <= to_date:
            chunk_end = min(cursor + timedelta(days=chunk_days - 1), to_date)
            yield cursor, chunk_end
            cursor = chunk_end + timedelta(days=1)

    def _fetch_corp_actions_api(
        self,
        session: requests.Session,
        from_date: date,
        to_date: date,
    ) -> pd.DataFrame | None:
        """
        Call the NSE corporate actions JSON API for a single date chunk.
        Returns None on any failure so the caller can fall back to Playwright.
        """
        # NSE date format for this API: DD-MM-YYYY
        params = {
            "index": "equities",
            "from_date": from_date.strftime("%d-%m-%Y"),
            "to_date":   to_date.strftime("%d-%m-%Y"),
        }
        try:
            resp = session.get(
                NSE_CORP_ACTIONS_API,
                params=params,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.warning("Corp actions API error: %s", exc)
            return None

        # API returns a list of dicts directly, or wrapped under a key
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("data", data.get("records", []))
        else:
            logger.warning("Corp actions API returned unexpected type: %s", type(data))
            return None

        if not records:
            logger.info("Corp actions API returned 0 records for %s → %s", from_date, to_date)
            return pd.DataFrame()

        return pd.DataFrame(records)

    def _fetch_corp_actions_playwright(
        self,
        from_date: date,
        to_date: date,
    ) -> pd.DataFrame | None:
        """
        Scrape NSE corporate actions page with a headless Chromium browser.

        Navigates the corporate actions page, applies date filters, and
        extracts all table rows including across paginated pages.
        Returns None on unrecoverable errors.
        """
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        rows: list[dict] = []

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(
                    user_agent=_BROWSER_HEADERS["User-Agent"],
                    locale="en-US",
                )
                page = ctx.new_page()

                # Cookie handshake: visit homepage before the target page
                page.goto(NSE_BASE, timeout=30_000)
                page.wait_for_timeout(2_000)

                logger.info("Playwright: navigating to corporate actions page")
                page.goto(NSE_CORP_ACTIONS_PAGE, timeout=30_000)
                page.wait_for_timeout(3_000)

                # Fill date range filters
                # NSE uses DD-MM-YYYY in its date inputs
                fmt = "%d-%m-%Y"
                self._pw_fill_date_filter(page, from_date.strftime(fmt), to_date.strftime(fmt))

                # Wait for the data table to appear
                try:
                    page.wait_for_selector("table", timeout=15_000)
                except PWTimeout:
                    logger.warning("Playwright: table did not appear within timeout")
                    browser.close()
                    return None

                # Paginate and collect all rows
                page_num = 1
                while True:
                    logger.info("Playwright: extracting page %d", page_num)
                    page_rows = self._pw_extract_table_rows(page)
                    if not page_rows:
                        break
                    rows.extend(page_rows)

                    # Try to click "Next" pagination button
                    next_btn = page.query_selector(
                        "a[aria-label='Next'], button:has-text('Next'), li.next a"
                    )
                    if not next_btn or not next_btn.is_enabled():
                        break
                    next_btn.click()
                    page.wait_for_timeout(2_000)
                    page_num += 1

                browser.close()

        except Exception as exc:
            logger.warning("Playwright scraping failed: %s", exc)
            return None

        if not rows:
            logger.warning("Playwright: extracted 0 rows from corporate actions page")
            return pd.DataFrame()

        return pd.DataFrame(rows)

    @staticmethod
    def _pw_fill_date_filter(page, from_date_str: str, to_date_str: str) -> None:
        """
        Fill date range inputs on the NSE corporate actions page.
        NSE uses various input selectors across site versions; try common ones.
        """
        date_input_pairs = [
            ("#fromDate", "#toDate"),
            ("input[name='fromDate']", "input[name='toDate']"),
            ("input[placeholder='From Date']", "input[placeholder='To Date']"),
        ]
        for from_sel, to_sel in date_input_pairs:
            try:
                if page.query_selector(from_sel):
                    page.fill(from_sel, from_date_str)
                    page.fill(to_sel, to_date_str)
                    # Click search/filter button
                    for btn_sel in ("button[type='submit']", "#search", "button:has-text('Search')"):
                        btn = page.query_selector(btn_sel)
                        if btn:
                            btn.click()
                            page.wait_for_timeout(2_000)
                            break
                    return
            except Exception:
                continue
        logger.warning("Playwright: could not locate date filter inputs — using page defaults")

    @staticmethod
    def _pw_extract_table_rows(page) -> list[dict]:
        """Extract all data rows from the visible table on the page."""
        return page.evaluate("""
            () => {
                const table = document.querySelector('table');
                if (!table) return [];
                const headers = Array.from(table.querySelectorAll('thead th, thead td'))
                                     .map(th => th.innerText.trim());
                if (!headers.length) return [];
                return Array.from(table.querySelectorAll('tbody tr')).map(tr => {
                    const cells = Array.from(tr.querySelectorAll('td'))
                                       .map(td => td.innerText.trim());
                    const row = {};
                    headers.forEach((h, i) => { row[h] = cells[i] || ''; });
                    return row;
                }).filter(r => Object.values(r).some(v => v !== ''));
            }
        """)

    def _normalize_corp_actions_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map NSE API field names to canonical column names.
        Handles both JSON API responses and Playwright-scraped table headers.
        """
        # Rename API fields using the constant mapping
        rename_map = {k: v for k, v in _CORP_ACTION_API_COLUMNS.items() if k in df.columns}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Also uppercase any remaining column names (handles Playwright scrape headers)
        df.columns = [c.strip().upper() for c in df.columns]

        # Playwright scrape produces human-readable headers — map common ones
        scrape_aliases = {
            "SYMBOL": "SYMBOL",
            "PURPOSE": "ACTION_TYPE_RAW",
            "SUBJECT": "ACTION_TYPE_RAW",
            "EX DATE": "EX_DATE",
            "EX-DATE": "EX_DATE",
            "RECORD DATE": "RECORD_DATE",
            "RECORD-DATE": "RECORD_DATE",
            "PAYMENT DATE": "PAYMENT_DATE",
            "PAYMENT-DATE": "PAYMENT_DATE",
            "COMPANY NAME": "COMPANY_NAME",
            "COMPANY": "COMPANY_NAME",
        }
        scrape_rename = {k: v for k, v in scrape_aliases.items() if k in df.columns and k != v}
        if scrape_rename:
            df.rename(columns=scrape_rename, inplace=True)

        return df.reset_index(drop=True)

    def _validate_corp_actions(self, df: pd.DataFrame) -> None:
        """
        Validate corporate actions DataFrame.
        Hard fail on missing critical columns; soft warnings otherwise.
        """
        required = ["SYMBOL", "EX_DATE", "ACTION_TYPE_RAW"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Corporate actions missing required columns: {missing}. "
                f"Columns present: {list(df.columns)}"
            )

        null_symbol = df["SYMBOL"].isna().sum()
        if null_symbol:
            logger.warning("%d corporate action rows have a missing SYMBOL", null_symbol)

        null_exdate = df["EX_DATE"].isna().sum()
        if null_exdate:
            logger.warning("%d corporate action rows have a missing EX_DATE", null_exdate)

        logger.info(
            "Corporate actions validation passed: %d rows, %d missing symbol, "
            "%d missing ex_date",
            len(df), null_symbol, null_exdate,
        )

    # ── step 5d stub ─────────────────────────────────────────────────────────

    def consolidate_to_staging(self) -> None:
        """Merge all daily raw files in data/raw/ into consolidated staging files."""
        raise NotImplementedError("Step 5d — implement consolidate_to_staging()")