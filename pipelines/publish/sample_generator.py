"""
SampleGenerator — produces tier-based release artifacts from curated data.

Tier structure:
  public/     — free sample (100 securities, 100 corporate actions)
  paid_tier_1 — Starter/Professional (full securities, 3yr actions, Parquet)
  paid_tier_2 — Enterprise (full history, Parquet)

All exports carry a SHA-256 checksum file alongside them.
"""

import hashlib
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

PUBLIC_SAMPLE_SIZE = 100
TIER1_SECURITY_LIMIT = 1000
TIER1_YEARS_LOOKBACK = 3
TIER2_FULL_HISTORY = True


class SampleGenerator:
    """
    Reads curated CSVs and writes tier-appropriate export files.

    Usage:
        gen   = SampleGenerator()
        paths = gen.generate_public_samples(date.today())
        paths = gen.generate_tier1_exports(date.today())
        paths = gen.generate_tier2_exports(date.today())
    """

    def __init__(
        self,
        curated_dir: Path = CURATED_DIR,
        samples_dir: Path = SAMPLES_DIR,
    ):
        self.curated_dir = Path(curated_dir)
        self.samples_dir = Path(samples_dir)

    # ── public (free) tier ────────────────────────────────────────────────────

    def generate_public_samples(self, run_date: date) -> dict[str, Path]:
        """
        Generate free-tier sample files.

        Outputs:
          public/nse_active_securities_sample_{date}.csv
          public/corporate_actions_sample_{date}.csv
        """
        out_dir = self.samples_dir / "public"
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = run_date.strftime("%Y%m%d")
        paths: dict[str, Path] = {}

        # Active securities sample
        sec_path = self.curated_dir / "dim_security_master.csv"
        if sec_path.exists():
            df = pd.read_csv(sec_path)
            if "active_flag" in df.columns:
                df = df[df["active_flag"] == True]  # noqa: E712
            sample_cols = [
                c
                for c in [
                    "nse_symbol",
                    "isin",
                    "company_name",
                    "sector",
                    "listing_date",
                    "active_flag",
                ]
                if c in df.columns
            ]
            sample = df[sample_cols].head(PUBLIC_SAMPLE_SIZE)
            out = out_dir / f"nse_active_securities_sample_{date_str}.csv"
            sample.to_csv(out, index=False)
            self._write_checksum(out)
            paths["securities_sample"] = out
            logger.info("Public securities sample: %d rows → %s", len(sample), out.name)

        # Corporate actions sample
        ca_path = self.curated_dir / "fact_corporate_action_event.csv"
        if ca_path.exists():
            df = pd.read_csv(ca_path)
            sample_cols = [
                c
                for c in [
                    "security_id",
                    "action_code",
                    "event_date",
                    "old_value",
                    "confidence_score",
                ]
                if c in df.columns
            ]
            if "event_date" in df.columns:
                df = df.sort_values("event_date", ascending=False)
            sample = df[sample_cols].head(PUBLIC_SAMPLE_SIZE)
            out = out_dir / f"corporate_actions_sample_{date_str}.csv"
            sample.to_csv(out, index=False)
            self._write_checksum(out)
            paths["actions_sample"] = out
            logger.info("Public actions sample: %d rows → %s", len(sample), out.name)

        return paths

    # ── tier 1 (Starter / Professional) ──────────────────────────────────────

    def generate_tier1_exports(self, run_date: date) -> dict[str, Path]:
        """
        Generate Starter/Professional tier exports (Parquet format).

        Outputs:
          paid_tier_1/extended_nse_master_{date}.csv
          paid_tier_1/corporate_actions_3yr_{date}.parquet
          paid_tier_1/adjustment_factors_{date}.parquet
        """
        out_dir = self.samples_dir / "paid_tier_1"
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = run_date.strftime("%Y%m%d")
        cutoff = pd.Timestamp(run_date) - pd.DateOffset(years=TIER1_YEARS_LOOKBACK)
        paths: dict[str, Path] = {}

        # Extended security master (all securities, up to TIER1_SECURITY_LIMIT)
        sec_path = self.curated_dir / "dim_security_master.csv"
        if sec_path.exists():
            df = pd.read_csv(sec_path).head(TIER1_SECURITY_LIMIT)
            out = out_dir / f"extended_nse_master_{date_str}.csv"
            df.to_csv(out, index=False)
            self._write_checksum(out)
            paths["extended_master"] = out
            logger.info("Tier-1 security master: %d rows → %s", len(df), out.name)

        # Corporate actions (last 3 years) as Parquet
        ca_path = self.curated_dir / "fact_corporate_action_event.csv"
        if ca_path.exists():
            df = pd.read_csv(ca_path)
            if "event_date" in df.columns:
                df = df.copy()
                df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
                df = df[df["event_date"] >= cutoff]
            out = out_dir / f"corporate_actions_3yr_{date_str}.parquet"
            self._write_parquet(df, out)
            paths["corp_actions_3yr"] = out
            logger.info(
                "Tier-1 corporate actions (3yr): %d rows → %s", len(df), out.name
            )

        # Adjustment factors as Parquet
        adj_path = self.curated_dir / "fact_adjustment_factor.csv"
        if adj_path.exists():
            df = pd.read_csv(adj_path)
            out = out_dir / f"adjustment_factors_{date_str}.parquet"
            self._write_parquet(df, out)
            paths["adjustment_factors"] = out
            logger.info("Tier-1 adjustment factors: %d rows → %s", len(df), out.name)

        return paths

    # ── tier 2 (Enterprise) ───────────────────────────────────────────────────

    def generate_tier2_exports(self, run_date: date) -> dict[str, Path]:
        """
        Generate Enterprise tier exports (full history, Parquet).

        Outputs:
          paid_tier_2/full_security_master_{date}.parquet
          paid_tier_2/corporate_actions_full_history_{date}.parquet
          paid_tier_2/adjustment_factors_full_{date}.parquet
          paid_tier_2/symbol_lineage_full_{date}.parquet
        """
        out_dir = self.samples_dir / "paid_tier_2"
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = run_date.strftime("%Y%m%d")
        paths: dict[str, Path] = {}

        exports = [
            ("dim_security_master.csv", f"full_security_master_{date_str}.parquet"),
            (
                "fact_corporate_action_event.csv",
                f"corporate_actions_full_history_{date_str}.parquet",
            ),
            (
                "fact_adjustment_factor.csv",
                f"adjustment_factors_full_{date_str}.parquet",
            ),
            (
                "fact_symbol_lineage_event.csv",
                f"symbol_lineage_full_{date_str}.parquet",
            ),
        ]
        for src_name, dst_name in exports:
            src = self.curated_dir / src_name
            if not src.exists():
                logger.info("Skipping %s — curated file not found", src_name)
                continue
            df = pd.read_csv(src)
            out = out_dir / dst_name
            self._write_parquet(df, out)
            paths[dst_name] = out
            logger.info("Tier-2 %s: %d rows → %s", src_name, len(df), out.name)

        return paths

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def compute_checksum(path: Path) -> str:
        """Return SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_checksum(self, path: Path) -> Path:
        """Write a .sha256 sidecar file alongside path."""
        checksum = self.compute_checksum(path)
        sha_path = path.with_suffix(path.suffix + ".sha256")
        sha_path.write_text(f"{checksum}  {path.name}\n")
        return sha_path

    @staticmethod
    def _write_parquet(df: pd.DataFrame, out: Path) -> None:
        """Write DataFrame to Parquet with snappy compression and a .sha256 sidecar."""
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, out, compression="snappy")
        # SHA256 for Parquet
        h = hashlib.sha256()
        with open(out, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        sha_path = out.with_suffix(".parquet.sha256")
        sha_path.write_text(f"{h.hexdigest()}  {out.name}\n")
