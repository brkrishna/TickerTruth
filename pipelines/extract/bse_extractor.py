"""
BSE Raw Data Extractor — equity master, bhavcopy, and corporate actions.

Step B2a: fetch_bse_equity_master()   — BSE scrip list via BSE API
Step B2b: fetch_bse_bhavcopy()        — BSE daily EOD zip
Step B2c: fetch_bse_corporate_actions() — BSE corporate action API
Step B2d: consolidate_bse_to_staging() — merge daily files to staging

Primary key difference from NSE: BSE uses numeric scrip codes (e.g. "500325")
instead of ticker symbols. ISIN is the natural join key to NSE.
"""

import json
import logging
import time
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_STAGING = PROJECT_ROOT / "data" / "staging"

BSE_EXCHANGE_ID = 2

# ── BSE equity master ─────────────────────────────────────────────────────────

BSE_EQUITY_MASTER_API = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
_BSE_EQUITY_MASTER_PARAMS = {
    "Group": "",
    "Scripcode": "",
    "industry": "",
    "segment": "Equity",
    "status": "Active",
    "ListType": "Main",
}

# ── BSE bhavcopy ──────────────────────────────────────────────────────────────

BSE_BHAVCOPY_BASE = "https://www.bseindia.com/download/BhavCopy/Equity/"

# ── BSE corporate actions ─────────────────────────────────────────────────────

BSE_CORP_ACTIONS_API = "https://api.bseindia.com/BseIndiaAPI/api/CorporateActionData/w"
CORP_ACTIONS_CHUNK_DAYS = 30
CORP_ACTIONS_DEFAULT_LOOKBACK_DAYS = 90

MIN_SCRIP_ROWS = 4000  # BSE main board has ~5000+ scrips

REQUIRED_SCRIP_COLUMNS = ["SCRIP_CODE", "ISIN", "SCRIP_NAME"]

# BSE API response key → canonical column name
_SCRIP_COLUMN_ALIASES: dict[str, str] = {
    "SCRIP_CD": "SCRIP_CODE",
    "SC_CD": "SCRIP_CODE",
    "Scrip_Cd": "SCRIP_CODE",
    "scripCode": "SCRIP_CODE",
    "SCRIP_CODE": "SCRIP_CODE",
    "SC_NAME": "SCRIP_NAME",
    "Scrip_Name": "SCRIP_NAME",
    "scrip_name": "SCRIP_NAME",
    "scripName": "SCRIP_NAME",
    "COMPANY_NAME": "COMPANY_NAME",
    "company_name": "COMPANY_NAME",
    "ISIN_CODE": "ISIN",
    "ISIN": "ISIN",
    "isin_code": "ISIN",
    "isin": "ISIN",
    "GROUP": "SEGMENT",
    "Segment": "SEGMENT",
    "Status": "STATUS",
    "STATUS": "STATUS",
    "DT_DATE": "LISTING_DATE",
    "listing_date": "LISTING_DATE",
}

_BHAVCOPY_COLUMN_ALIASES: dict[str, str] = {
    "SC_CODE": "SCRIP_CODE",
    "SC_NAME": "SCRIP_NAME",
    "SC_GROUP": "SEGMENT",
    "SC_TYPE": "SERIES",
    "OPEN": "OPEN",
    "HIGH": "HIGH",
    "LOW": "LOW",
    "CLOSE": "CLOSE",
    "LAST": "LAST",
    "PREVCLOSE": "PREVCLOSE",
    "NO_TRADES": "TOTALTRADES",
    "NET_TURNOV": "TOTTRDVAL",
}

_CORP_ACTION_COLUMN_ALIASES: dict[str, str] = {
    "scrip_code": "SCRIP_CODE",
    "SCRIP_CD": "SCRIP_CODE",
    "SC_CD": "SCRIP_CODE",
    "scrip_name": "SCRIP_NAME",
    "SC_NAME": "SCRIP_NAME",
    "Purpose": "ACTION_TYPE_RAW",
    "purpose": "ACTION_TYPE_RAW",
    "ExDate": "EX_DATE",
    "ex_date": "EX_DATE",
    "RdDate": "RECORD_DATE",
    "record_date": "RECORD_DATE",
    "PdDate": "PAYMENT_DATE",
    "payment_date": "PAYMENT_DATE",
    "BCStartDate": "BC_START_DATE",
    "BCEndDate": "BC_END_DATE",
}

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com",
}


class BSERawDataExtractor:
    """
    Downloads raw source files from BSE and saves them to data/raw/.

    Usage:
        extractor = BSERawDataExtractor()
        df = extractor.fetch_bse_equity_master()
    """

    def __init__(self, output_dir: Path = DATA_RAW):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── step B2a: BSE equity master ───────────────────────────────────────────

    def fetch_bse_equity_master(self) -> pd.DataFrame:
        """
        Download the BSE equity master via the BSE API.

        Returns a DataFrame keyed by SCRIP_CODE (numeric string like "500325").
        ISIN is the join key to NSE. STATUS column is present in the BSE response
        (unlike NSE's EQUITY_L.csv which lists only active securities).

        Saves raw file to data/raw/bse_equity_master_{YYYY-MM-DD}.csv.

        Raises:
            RuntimeError: if the API call fails.
            ValueError: if required columns are missing or row count is too low.
        """
        today = date.today().isoformat()
        out_path = self.output_dir / f"bse_equity_master_{today}.csv"

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Using cached BSE equity master: %s", out_path)
            return pd.read_csv(out_path, dtype={"SCRIP_CODE": str})

        logger.info("Fetching BSE equity master from API...")
        df = self._fetch_equity_master_api()

        if df is None or df.empty:
            raise RuntimeError(
                "BSE equity master API returned no data. "
                f"URL: {BSE_EQUITY_MASTER_API}. "
                "Check network connectivity or BSE API status."
            )

        df = self._normalize_scrip_columns(df)
        self._validate_equity_master(df)

        df.to_csv(out_path, index=False)
        logger.info("Saved %d BSE scrips → %s", len(df), out_path)
        return df

    def _fetch_equity_master_api(self) -> pd.DataFrame | None:
        try:
            resp = requests.get(
                BSE_EQUITY_MASTER_API,
                params=_BSE_EQUITY_MASTER_PARAMS,
                headers=_BROWSER_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.warning("BSE equity master API failed: %s", exc)
            return None

        # BSE API wraps the list in various envelope structures
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ("Table", "Table1", "data", "records"):
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break
            else:
                logger.warning(
                    "BSE equity master: unexpected response shape: %s",
                    list(data.keys()),
                )
                return None
        else:
            logger.warning("BSE equity master: unexpected type: %s", type(data))
            return None

        if not records:
            logger.warning("BSE equity master: API returned empty list")
            return pd.DataFrame()

        return pd.DataFrame(records)

    def _normalize_scrip_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        rename_map = {k: v for k, v in _SCRIP_COLUMN_ALIASES.items() if k in df.columns}
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Ensure SCRIP_CODE is always string (BSE sometimes returns int)
        if "SCRIP_CODE" in df.columns:
            df["SCRIP_CODE"] = df["SCRIP_CODE"].astype(str).str.strip().str.zfill(6)

        if "ISIN" in df.columns:
            df["ISIN"] = df["ISIN"].astype(str).str.strip().str.upper()
            df.loc[df["ISIN"].isin(["NAN", "NONE", ""]), "ISIN"] = None

        if "STATUS" not in df.columns:
            # BSE API filtered to active — synthesize STATUS
            df["STATUS"] = "Active"
            logger.info("BSE STATUS column absent — defaulted all rows to 'Active'")

        dedup_cols = [c for c in ["SCRIP_CODE"] if c in df.columns]
        if dedup_cols:
            before = len(df)
            df.drop_duplicates(subset=dedup_cols, keep="last", inplace=True)
            dropped = before - len(df)
            if dropped:
                logger.warning("Dropped %d duplicate SCRIP_CODE rows", dropped)

        return df.reset_index(drop=True)

    def _validate_equity_master(self, df: pd.DataFrame) -> None:
        missing = [c for c in REQUIRED_SCRIP_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"BSE equity master missing required columns: {missing}. "
                f"Columns present: {list(df.columns)}"
            )
        if len(df) < MIN_SCRIP_ROWS:
            raise ValueError(
                f"BSE equity master has only {len(df)} rows — expected ≥ {MIN_SCRIP_ROWS}. "
                "The download may be incomplete."
            )
        null_isin = df["ISIN"].isna().sum()
        if null_isin:
            logger.warning("BSE equity master: %d rows have a missing ISIN", null_isin)
        logger.info(
            "BSE equity master validation passed: %d scrips, %d missing ISIN",
            len(df),
            null_isin,
        )

    # ── step B2b: BSE bhavcopy ────────────────────────────────────────────────

    def fetch_bse_bhavcopy(self, trading_date: date) -> pd.DataFrame:
        """
        Download BSE equity bhavcopy (EOD) for a given trading date.

        URL pattern:
            https://www.bseindia.com/download/BhavCopy/Equity/EQ{DDMMYYYY}_CSV.ZIP

        Returns DataFrame with columns: SCRIP_CODE, SCRIP_NAME, OPEN, HIGH, LOW,
        CLOSE, LAST, PREVCLOSE, TOTALTRADES, TOTTRDVAL.

        Raises:
            RuntimeError: if the download fails (holiday, network error).
            ValueError: if required columns are missing or OHLC sanity fails.
        """
        out_path = self.output_dir / f"bse_bhavcopy_{trading_date.isoformat()}.csv"

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Using cached BSE bhavcopy: %s", out_path)
            return pd.read_csv(out_path, dtype={"SCRIP_CODE": str})

        url = self._bse_bhavcopy_url(trading_date)
        logger.info("Downloading BSE bhavcopy from %s", url)

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _BROWSER_HEADERS["User-Agent"]},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                raise RuntimeError(
                    f"BSE bhavcopy not found for {trading_date} (HTTP 404). "
                    "Likely a market holiday, weekend, or file not yet published."
                ) from exc
            raise RuntimeError(
                f"Failed to download BSE bhavcopy for {trading_date}: {exc}"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to download BSE bhavcopy for {trading_date}: {exc}"
            ) from exc

        df = self._extract_bhavcopy_zip(resp.content, trading_date)
        df = self._normalize_bhavcopy_columns(df)
        self._validate_bhavcopy(df, trading_date)

        df.to_csv(out_path, index=False)
        logger.info("Saved %d rows BSE bhavcopy → %s", len(df), out_path)
        return df

    def _bse_bhavcopy_url(self, trading_date: date) -> str:
        """Build BSE archives URL: EQ{DDMMYYYY}_CSV.ZIP"""
        dd = trading_date.strftime("%d")
        mm = trading_date.strftime("%m")
        yyyy = trading_date.strftime("%Y")
        return f"{BSE_BHAVCOPY_BASE}EQ{dd}{mm}{yyyy}_CSV.ZIP"

    def _extract_bhavcopy_zip(self, content: bytes, trading_date: date) -> pd.DataFrame:
        import zipfile

        try:
            zf = zipfile.ZipFile(BytesIO(content))
        except zipfile.BadZipFile as exc:
            raise RuntimeError(
                f"Downloaded BSE bhavcopy for {trading_date} is not a valid ZIP."
            ) from exc

        csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_files:
            raise RuntimeError(
                f"No CSV inside BSE bhavcopy ZIP for {trading_date}. "
                f"Contents: {zf.namelist()}"
            )

        csv_name = next(
            (n for n in csv_files if n.upper().startswith("EQ")),
            csv_files[0],
        )
        logger.info("Extracting %s from BSE bhavcopy ZIP", csv_name)
        return pd.read_csv(zf.open(csv_name))

    def _normalize_bhavcopy_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [c.strip().upper() for c in df.columns]
        rename_map = {
            k: v for k, v in _BHAVCOPY_COLUMN_ALIASES.items() if k in df.columns
        }
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        if "SCRIP_CODE" in df.columns:
            df["SCRIP_CODE"] = df["SCRIP_CODE"].astype(str).str.strip().str.zfill(6)

        unnamed = [c for c in df.columns if c.startswith("UNNAMED:")]
        if unnamed:
            df.drop(columns=unnamed, inplace=True)

        return df.reset_index(drop=True)

    def _validate_bhavcopy(self, df: pd.DataFrame, trading_date: date) -> None:
        required = ["SCRIP_CODE", "OPEN", "HIGH", "LOW", "CLOSE"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"BSE bhavcopy for {trading_date} missing required columns: {missing}. "
                f"Columns: {list(df.columns)}"
            )
        if len(df) < 500:
            raise ValueError(
                f"BSE bhavcopy for {trading_date} has only {len(df)} rows — "
                "expected ≥ 500. File may be incomplete."
            )
        ohlc_ok = (df["LOW"] <= df["CLOSE"] + 0.01) & (df["CLOSE"] <= df["HIGH"] + 0.01)
        bad = (~ohlc_ok).sum()
        if bad:
            logger.warning(
                "%d rows in BSE bhavcopy for %s fail OHLC sanity", bad, trading_date
            )
        logger.info(
            "BSE bhavcopy validation passed: %d rows for %s", len(df), trading_date
        )

    # ── step B2c: BSE corporate actions ──────────────────────────────────────

    def fetch_bse_corporate_actions(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> pd.DataFrame:
        """
        Fetch BSE corporate action announcements for a date range.

        BSE API uses DD/MM/YYYY date format (different from NSE's DD-MM-YYYY).
        Chunks large ranges into 30-day windows to respect API limits.

        Returns DataFrame with columns: SCRIP_CODE, SCRIP_NAME, ACTION_TYPE_RAW,
        EX_DATE, RECORD_DATE, PAYMENT_DATE, BC_START_DATE, BC_END_DATE.

        Raises:
            RuntimeError: if the API fails and no stale cache is available.
        """
        to_date = to_date or date.today()
        from_date = from_date or (
            to_date - timedelta(days=CORP_ACTIONS_DEFAULT_LOOKBACK_DAYS)
        )

        out_path = self.output_dir / (
            f"bse_actions_{from_date.isoformat()}_{to_date.isoformat()}.csv"
        )

        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Using cached BSE corporate actions: %s", out_path)
            return pd.read_csv(out_path, dtype={"SCRIP_CODE": str})

        chunks = list(self._date_chunks(from_date, to_date, CORP_ACTIONS_CHUNK_DAYS))
        logger.info(
            "Fetching BSE corporate actions %s → %s in %d chunk(s)",
            from_date,
            to_date,
            len(chunks),
        )

        all_frames: list[pd.DataFrame] = []
        for chunk_from, chunk_to in chunks:
            df = self._fetch_corp_actions_chunk(chunk_from, chunk_to)
            if df is not None and not df.empty:
                all_frames.append(df)
            time.sleep(1.0)

        if not all_frames:
            stale = self._stale_corp_actions_fallback()
            if stale is not None:
                return stale
            raise RuntimeError(
                f"Failed to fetch BSE corporate actions {from_date} → {to_date}. "
                "No stale cache available."
            )

        df = pd.concat(all_frames, ignore_index=True)
        df = self._normalize_corp_actions_columns(df)
        df.drop_duplicates(
            subset=["SCRIP_CODE", "EX_DATE", "ACTION_TYPE_RAW"],
            keep="last",
            inplace=True,
        )
        self._validate_corp_actions(df)

        df.to_csv(out_path, index=False)
        logger.info("Saved %d BSE corporate action rows → %s", len(df), out_path)
        return df

    def _fetch_corp_actions_chunk(
        self, from_date: date, to_date: date
    ) -> pd.DataFrame | None:
        """Fetch one 30-day chunk from the BSE corporate actions API."""
        # BSE API requires DD/MM/YYYY
        fmt = "%d/%m/%Y"
        params = {
            "scripcode": "",
            "FromDate": from_date.strftime(fmt),
            "ToDate": to_date.strftime(fmt),
            "CorporateAcType": "",
        }
        try:
            resp = requests.get(
                BSE_CORP_ACTIONS_API,
                params=params,
                headers=_BROWSER_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.warning(
                "BSE corp actions API error for %s→%s: %s", from_date, to_date, exc
            )
            return None

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ("Table", "Table1", "data", "records"):
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break
            else:
                records = []
        else:
            records = []

        if not records:
            logger.info("BSE corp actions: 0 records for %s → %s", from_date, to_date)
            return pd.DataFrame()

        return pd.DataFrame(records)

    def _normalize_corp_actions_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            k: v for k, v in _CORP_ACTION_COLUMN_ALIASES.items() if k in df.columns
        }
        if rename_map:
            df.rename(columns=rename_map, inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]

        if "SCRIP_CODE" in df.columns:
            df["SCRIP_CODE"] = df["SCRIP_CODE"].astype(str).str.strip().str.zfill(6)

        return df.reset_index(drop=True)

    def _validate_corp_actions(self, df: pd.DataFrame) -> None:
        required = ["SCRIP_CODE", "EX_DATE", "ACTION_TYPE_RAW"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"BSE corporate actions missing required columns: {missing}. "
                f"Columns: {list(df.columns)}"
            )
        null_code = df["SCRIP_CODE"].isna().sum()
        if null_code:
            logger.warning("BSE corp actions: %d rows missing SCRIP_CODE", null_code)
        logger.info("BSE corp actions validation passed: %d rows", len(df))

    def _stale_corp_actions_fallback(self) -> pd.DataFrame | None:
        candidates = sorted(
            (
                f
                for f in self.output_dir.glob("bse_actions_*.csv")
                if f.stat().st_size > 0
            ),
            reverse=True,
        )
        if not candidates:
            return None
        latest = candidates[0]
        logger.warning(
            "All live BSE fetch methods failed — using stale cache: %s", latest.name
        )
        try:
            return pd.read_csv(latest, dtype={"SCRIP_CODE": str})
        except Exception as exc:
            logger.warning("Stale BSE cache read failed: %s", exc)
            return None

    # ── step B2d: consolidate BSE to staging ─────────────────────────────────

    def consolidate_bse_to_staging(
        self,
        staging_dir: Path = DATA_STAGING,
        run_date: date | None = None,
    ) -> dict:
        """
        Merge all daily BSE raw files into consolidated staging files.

        Mirrors the NSE consolidate_to_staging() pattern. Writes:
          - bse_scrips_consolidated.csv
          - bse_bhavcopy_consolidated.csv
          - bse_actions_consolidated.csv

        Returns:
            dict with keys 'scrips', 'bhavcopy', 'actions', each containing
            files_found, rows_before_dedup, rows_after_dedup.
        """
        staging_dir = Path(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)

        report: dict = {}

        report["scrips"] = self._consolidate_source(
            pattern="bse_equity_master_*.csv",
            out_file=staging_dir / "bse_scrips_consolidated.csv",
            dedup_cols=["SCRIP_CODE"],
            label="BSE scrips",
        )

        report["bhavcopy"] = self._consolidate_source(
            pattern="bse_bhavcopy_*.csv",
            out_file=staging_dir / "bse_bhavcopy_consolidated.csv",
            dedup_cols=["SCRIP_CODE", "TRADING_DATE"],
            label="BSE bhavcopy",
        )

        report["actions"] = self._consolidate_source(
            pattern="bse_actions_*.csv",
            out_file=staging_dir / "bse_actions_consolidated.csv",
            dedup_cols=["SCRIP_CODE", "EX_DATE", "ACTION_TYPE_RAW"],
            label="BSE corporate actions",
        )

        return report

    def _consolidate_source(
        self,
        pattern: str,
        out_file: Path,
        dedup_cols: list[str],
        label: str,
    ) -> dict:
        files = sorted(self.output_dir.glob(pattern))
        result = {
            "files_found": len(files),
            "rows_before_dedup": 0,
            "rows_after_dedup": 0,
        }

        if not files:
            logger.warning("%s: no raw files found matching %s", label, pattern)
            return result

        frames: list[pd.DataFrame] = []
        for f in files:
            try:
                df = pd.read_csv(f, dtype={"SCRIP_CODE": str})
                frames.append(df)
            except Exception as exc:
                logger.warning("%s: skipping %s — %s", label, f.name, exc)

        if not frames:
            return result

        combined = pd.concat(frames, ignore_index=True)
        result["rows_before_dedup"] = len(combined)

        valid_dedup = [c for c in dedup_cols if c in combined.columns]
        if valid_dedup:
            combined.drop_duplicates(subset=valid_dedup, keep="last", inplace=True)

        combined.reset_index(drop=True, inplace=True)
        result["rows_after_dedup"] = len(combined)
        combined.to_csv(out_file, index=False)
        logger.info(
            "%s: %d files → %d rows → %s",
            label,
            len(files),
            result["rows_after_dedup"],
            out_file.name,
        )
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _date_chunks(from_date: date, to_date: date, chunk_days: int):
        cursor = from_date
        while cursor <= to_date:
            chunk_end = min(cursor + timedelta(days=chunk_days - 1), to_date)
            yield cursor, chunk_end
            cursor = chunk_end + timedelta(days=1)
