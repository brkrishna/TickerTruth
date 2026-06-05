"""
HuggingFacePublisher — pushes the refreshed security master CSV to the
tickertruth/nse-india-security-master dataset on HuggingFace.

Reads from data/curated/dim_security_master.csv, projects to the public
5-column schema, and uploads via the huggingface_hub API.

Requires: HF_TOKEN env var (Write-scoped HuggingFace access token).
"""

import logging
import os
from datetime import date
from io import StringIO
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

REPO_ID = "tickertruth/nse-india-security-master"
PUBLIC_COLUMNS = ["nse_symbol", "isin", "company_name", "listing_date", "active_flag"]


class HuggingFacePublisher:
    """
    Publishes the refreshed NSE security master to HuggingFace Datasets.

    Usage:
        publisher = HuggingFacePublisher()
        publisher.publish(run_date)
    """

    def __init__(self, curated_dir: Path = PROJECT_ROOT / "data" / "curated"):
        self.curated_dir = Path(curated_dir)

    def publish(self, run_date: date) -> bool:
        """
        Project dim_security_master to the public schema and upload to HuggingFace.

        Returns True on success, False on any failure.
        """
        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            logger.warning(
                "[huggingface] HF_TOKEN not set — skipping HuggingFace publish"
            )
            return False

        try:
            from huggingface_hub import HfApi
        except ImportError:
            logger.error(
                "[huggingface] huggingface_hub is not installed. "
                "Run: pip install huggingface_hub"
            )
            return False

        source = self.curated_dir / "dim_security_master.csv"
        if not source.exists():
            logger.error(
                "[huggingface] dim_security_master.csv not found at %s", source
            )
            return False

        try:
            df = pd.read_csv(source)
        except Exception as exc:
            logger.error("[huggingface] Failed to read %s: %s", source, exc)
            return False

        missing = [c for c in PUBLIC_COLUMNS if c not in df.columns]
        if missing:
            logger.error(
                "[huggingface] Missing columns in dim_security_master: %s", missing
            )
            return False

        public_df = df[PUBLIC_COLUMNS].copy()
        logger.info(
            "[huggingface] Preparing %d rows for upload (run_date=%s)",
            len(public_df),
            run_date,
        )

        csv_bytes = public_df.to_csv(index=False).encode("utf-8")

        try:
            api = HfApi(token=token)
            api.upload_file(
                path_or_fileobj=csv_bytes,
                path_in_repo="data/nse_security_master.csv",
                repo_id=REPO_ID,
                repo_type="dataset",
                commit_message=f"nightly refresh: {run_date.isoformat()}",
            )
            logger.info(
                "[huggingface] Uploaded nse_security_master.csv (%d rows) → %s",
                len(public_df),
                REPO_ID,
            )
        except Exception as exc:
            logger.error("[huggingface] Upload failed: %s", exc)
            return False

        return True
