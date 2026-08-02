"""
Experiment: fetch NSE's ~15-min-delayed quote data for a whole index in one call.

This is NOT part of the reference-data pipeline (extract -> normalize -> ...).
It's a standalone probe to see whether NSE's undocumented equity-stockIndices
API is viable as a future intraday-quotes source. Nothing here writes to
data/raw/ or data/staging/, and it is not wired into pipelines/run.py.

Usage:
    python scripts/experiment_nse_delayed_quotes.py
    python scripts/experiment_nse_delayed_quotes.py --index "NIFTY BANK"
    python scripts/experiment_nse_delayed_quotes.py --index "NIFTY 50" --index "NIFTY BANK"
"""

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NSE_BASE = "https://www.nseindia.com"
NSE_STOCK_INDICES_API = f"{NSE_BASE}/api/equity-stockIndices"

# Retry tuning — NSE's Akamai layer rate-limits and occasionally 403s
# transiently even with a valid session, so retries with backoff are worth
# it before concluding the endpoint is unreachable.
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0
RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}

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

OUT_DIR = Path(__file__).parent / "experiment_output"


def _sleep_backoff(attempt: int) -> None:
    """Exponential backoff with jitter: ~2s, 4s, 8s, 16s (+/- 0-1s)."""
    delay = BACKOFF_BASE_SECONDS * (2**attempt) + random.uniform(0, 1)
    logger.info("Retrying in %.1fs...", delay)
    time.sleep(delay)


def _request_with_retry(
    session: requests.Session, url: str, **kwargs
) -> requests.Response:
    """
    GET with retries on transient failures (connection errors, timeouts, and
    the status codes in RETRYABLE_STATUS_CODES). Raises on the final attempt.
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=kwargs.pop("timeout", 30), **kwargs)
            if resp.status_code in RETRYABLE_STATUS_CODES:
                logger.warning(
                    "Attempt %d/%d: HTTP %d from %s",
                    attempt + 1,
                    MAX_RETRIES,
                    resp.status_code,
                    url,
                )
                if attempt < MAX_RETRIES - 1:
                    _sleep_backoff(attempt)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Attempt %d/%d: request error for %s — %s",
                attempt + 1,
                MAX_RETRIES,
                url,
                exc,
            )
            if attempt < MAX_RETRIES - 1:
                _sleep_backoff(attempt)
    raise last_exc  # exhausted all retries


def get_session() -> requests.Session:
    """Same cookie handshake pattern as RawDataExtractor._get_session(), with retries."""
    session = requests.Session()
    session.headers.update(_BROWSER_HEADERS)

    logger.info("Performing NSE cookie handshake...")
    resp = _request_with_retry(session, NSE_BASE, timeout=15)
    logger.info("Cookie handshake succeeded (HTTP %s)", resp.status_code)

    time.sleep(1.5)
    return session


def fetch_delayed_quotes(session: requests.Session, index: str) -> dict:
    """
    Call the equity-stockIndices API for one NSE index, with retries.

    Returns the raw parsed JSON. Notable fields per constituent (under
    "data"): symbol, lastPrice, change, pChange, open, dayHigh, dayLow,
    previousClose, totalTradedVolume, and a top-level "timestamp" giving
    the as-of time (which is where the ~15-min delay shows up).
    """
    resp = _request_with_retry(
        session,
        NSE_STOCK_INDICES_API,
        params={"index": index},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        action="append",
        dest="indices",
        help="NSE index name to fetch quotes for. Repeatable. Default: 'NIFTY 50'",
    )
    args = parser.parse_args()
    indices = args.indices or ["NIFTY 50"]

    try:
        session = get_session()
    except requests.RequestException as exc:
        logger.error("Cookie handshake failed after %d attempts: %s", MAX_RETRIES, exc)
        return 1

    OUT_DIR.mkdir(exist_ok=True)
    had_failure = False

    for i, index in enumerate(indices):
        if i > 0:
            time.sleep(1.5)  # space out calls between indices

        try:
            payload = fetch_delayed_quotes(session, index)
        except requests.RequestException as exc:
            logger.error(
                "Fetch failed for index '%s' after %d attempts: %s",
                index,
                MAX_RETRIES,
                exc,
            )
            had_failure = True
            continue

        constituents = payload.get("data", [])
        as_of = payload.get("timestamp", "unknown")
        logger.info(
            "Fetched %d constituents for index '%s' — as-of timestamp: %s",
            len(constituents),
            index,
            as_of,
        )

        if constituents:
            sample = constituents[0]
            logger.info("Sample row: %s", json.dumps(sample, indent=2)[:500])

        out_path = OUT_DIR / f"delayed_quotes_{index.replace(' ', '_')}.json"
        out_path.write_text(json.dumps(payload, indent=2))
        logger.info("Full response written to %s", out_path)

    return 1 if had_failure else 0


if __name__ == "__main__":
    sys.exit(main())
