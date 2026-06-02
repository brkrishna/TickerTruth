"""
AccessManager — buyer registry, signed URL generation, and download audit log.

Designed for manual commercial delivery:
  1. Operator creates a buyer record (create_buyer)
  2. Operator generates a signed R2 URL for their tier bundle (generate_signed_url)
  3. Operator sends URL to buyer via email
  4. Downloads are logged automatically (log_download)

All state is stored in flat CSV files (data/buyers/) — no database needed for MVP.
R2 access is via boto3 with Cloudflare-compatible endpoint.
"""

import csv
import logging
import os
import uuid
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = Path(__file__).parent / "config.yaml"
BUYERS_DIR = PROJECT_ROOT / "data" / "buyers"
BUYERS_CSV = BUYERS_DIR / "buyers.csv"
DOWNLOAD_LOG = BUYERS_DIR / "download_log.csv"

_BUYER_FIELDS = ["buyer_id", "name", "email", "tier", "created_date", "status", "notes"]
_DOWNLOAD_FIELDS = [
    "log_id",
    "buyer_id",
    "tier",
    "s3_key",
    "signed_url",
    "generated_at",
    "expires_at",
]


class AccessManager:
    """
    Manages buyer records and generates signed download URLs.

    Usage:
        mgr     = AccessManager()
        buyer   = mgr.create_buyer("Acme Quant", "data@acme.in", "starter")
        url     = mgr.generate_signed_url(buyer["buyer_id"], "releases/20240601/starter/...")
        mgr.log_download(buyer["buyer_id"], "starter", s3_key, url)
    """

    def __init__(
        self,
        buyers_csv: Path = BUYERS_CSV,
        download_log: Path = DOWNLOAD_LOG,
        config_path: Path = CONFIG_PATH,
    ):
        self.buyers_csv = Path(buyers_csv)
        self.download_log = Path(download_log)
        self._cfg = self._load_config(config_path)
        self.buyers_csv.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_config(path: Path) -> dict:
        try:
            with open(path) as fh:
                return yaml.safe_load(fh)
        except FileNotFoundError:
            return {}

    # ── buyer registry ────────────────────────────────────────────────────────

    def create_buyer(
        self,
        name: str,
        email: str,
        tier: str,
        notes: str = "",
    ) -> dict:
        """
        Add a new buyer to the registry.

        Args:
            name:  Full name or organisation
            email: Contact email for download links
            tier:  explorer | starter | professional | enterprise
            notes: Free-text notes (payment ref, contract date, etc.)

        Returns:
            Buyer record dict with generated buyer_id.

        Raises:
            ValueError if email is already registered.
        """
        existing = self.list_buyers()
        if any(b["email"].lower() == email.lower() for b in existing):
            raise ValueError(f"Buyer with email {email!r} already exists.")

        record = {
            "buyer_id": str(uuid.uuid4())[:8].upper(),
            "name": name,
            "email": email,
            "tier": tier,
            "created_date": date.today().isoformat(),
            "status": "active",
            "notes": notes,
        }
        self._append_csv(self.buyers_csv, _BUYER_FIELDS, record)
        logger.info("Created buyer %s (%s) — tier: %s", record["buyer_id"], email, tier)
        return record

    def list_buyers(
        self, tier: str | None = None, status: str = "active"
    ) -> list[dict]:
        """
        Return buyer records, optionally filtered by tier and/or status.

        Args:
            tier:   Filter to this tier only (None = all tiers)
            status: Filter to this status (default: 'active'; None = all)

        Returns:
            List of buyer record dicts.
        """
        if not self.buyers_csv.exists():
            return []
        with open(self.buyers_csv, newline="") as fh:
            rows = list(csv.DictReader(fh))
        if status:
            rows = [r for r in rows if r.get("status") == status]
        if tier:
            rows = [r for r in rows if r.get("tier") == tier]
        return rows

    def get_buyer(self, buyer_id: str) -> dict | None:
        """Look up a buyer by buyer_id. Returns None if not found."""
        return next(
            (b for b in self.list_buyers(status=None) if b["buyer_id"] == buyer_id),
            None,
        )

    def deactivate_buyer(self, buyer_id: str) -> bool:
        """
        Set buyer status to 'inactive' (non-destructive — record is retained).

        Returns True if the buyer was found and updated, False otherwise.
        """
        buyers = self.list_buyers(status=None)
        updated = False
        for b in buyers:
            if b["buyer_id"] == buyer_id:
                b["status"] = "inactive"
                updated = True
                break
        if updated:
            self._rewrite_csv(self.buyers_csv, _BUYER_FIELDS, buyers)
            logger.info("Deactivated buyer %s", buyer_id)
        return updated

    # ── signed URL generation ─────────────────────────────────────────────────

    def generate_signed_url(
        self,
        buyer_id: str,
        s3_key: str,
        expires_hours: int | None = None,
    ) -> str:
        """
        Generate a pre-signed R2 download URL for a bundle file.

        Requires R2 credentials in environment:
            R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET

        Args:
            buyer_id:     Buyer record ID (used for audit logging)
            s3_key:       Object key within the R2 bucket
            expires_hours: URL lifetime in hours (default: from config, 168 = 7 days)

        Returns:
            Pre-signed HTTPS URL string.

        Raises:
            RuntimeError if R2 credentials are not configured.
            ValueError if buyer_id is not found.
        """
        buyer = self.get_buyer(buyer_id)
        if not buyer:
            raise ValueError(f"Buyer not found: {buyer_id}")
        if buyer.get("status") != "active":
            raise ValueError(f"Buyer {buyer_id} is not active")

        r2_cfg = self._cfg.get("r2", {})
        expires_hours = expires_hours or r2_cfg.get("signed_url_expires_hours", 168)
        endpoint = os.environ.get(r2_cfg.get("endpoint_env", "R2_ENDPOINT"), "")
        bucket = os.environ.get(r2_cfg.get("bucket_env", "R2_BUCKET"), "")
        access_key = os.environ.get(
            r2_cfg.get("access_key_env", "R2_ACCESS_KEY_ID"), ""
        )
        secret_key = os.environ.get(
            r2_cfg.get("secret_key_env", "R2_SECRET_ACCESS_KEY"), ""
        )

        if not all([endpoint, bucket, access_key, secret_key]):
            raise RuntimeError(
                "R2 credentials not configured. Set R2_ENDPOINT, R2_BUCKET, "
                "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in environment."
            )

        signed_url = self._presign(
            endpoint, bucket, s3_key, access_key, secret_key, expires_hours
        )

        self.log_download(buyer_id, buyer["tier"], s3_key, signed_url, expires_hours)
        logger.info(
            "Generated signed URL for buyer %s (tier=%s, expires=%dh)",
            buyer_id,
            buyer["tier"],
            expires_hours,
        )
        return signed_url

    @staticmethod
    def _presign(
        endpoint: str,
        bucket: str,
        key: str,
        access_key: str,
        secret_key: str,
        expires_hours: int,
    ) -> str:
        """Generate a pre-signed URL via boto3."""
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_hours * 3600,
        )

    # ── download audit log ────────────────────────────────────────────────────

    def log_download(
        self,
        buyer_id: str,
        tier: str,
        s3_key: str,
        signed_url: str,
        expires_hours: int = 168,
    ) -> dict:
        """
        Append a download record to the audit log.

        Returns the log record dict.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=expires_hours)
        record = {
            "log_id": str(uuid.uuid4())[:8].upper(),
            "buyer_id": buyer_id,
            "tier": tier,
            "s3_key": s3_key,
            "signed_url": signed_url,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._append_csv(self.download_log, _DOWNLOAD_FIELDS, record)
        return record

    def list_downloads(self, buyer_id: str | None = None) -> list[dict]:
        """Return download log entries, optionally filtered by buyer_id."""
        if not self.download_log.exists():
            return []
        with open(self.download_log, newline="") as fh:
            rows = list(csv.DictReader(fh))
        if buyer_id:
            rows = [r for r in rows if r.get("buyer_id") == buyer_id]
        return rows

    # ── CSV helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _append_csv(path: Path, fieldnames: list[str], record: dict) -> None:
        file_exists = path.exists()
        with open(path, "a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)

    @staticmethod
    def _rewrite_csv(path: Path, fieldnames: list[str], records: list[dict]) -> None:
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
