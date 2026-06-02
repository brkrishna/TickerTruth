"""
ManifestBuilder — generates the release manifest and maintains exports_log.csv.
"""

import csv
import logging
from datetime import date, datetime, timezone
from pathlib import Path


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"


class ManifestBuilder:
    """
    Builds a Markdown manifest for a release and appends to exports_log.csv.

    Usage:
        builder  = ManifestBuilder()
        manifest = builder.build_manifest(all_export_paths, date.today())
        builder.log_exports(all_export_paths, date.today())
    """

    def __init__(self, samples_dir: Path = SAMPLES_DIR):
        self.samples_dir = Path(samples_dir)

    def build_manifest(
        self,
        export_paths: dict[str, Path],
        run_date: date,
        extra_stats: dict | None = None,
    ) -> Path:
        """
        Generate a Markdown manifest file listing all exports with row counts,
        file sizes, and SHA-256 checksums.

        Args:
            export_paths: {label: Path} dict from SampleGenerator methods
            run_date:     Release date
            extra_stats:  Optional dict of additional pipeline statistics to include

        Returns:
            Path to the written manifest file.
        """
        date_str = run_date.strftime("%Y%m%d")
        out_path = self.samples_dir / "metadata" / f"manifest_{date_str}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Release Manifest — {run_date.isoformat()}",
            "",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Export Files",
            "",
            "| Label | File | Rows | Size | SHA-256 |",
            "|---|---|---|---|---|",
        ]

        for label, path in export_paths.items():
            if not path.exists():
                lines.append(f"| {label} | {path.name} | — | — | FILE MISSING |")
                continue

            size_kb = path.stat().st_size / 1024
            rows = self._count_rows(path)
            checksum = self._read_checksum(path)
            short_cs = checksum[:12] + "…" if checksum else "—"
            lines.append(
                f"| {label} | {path.name} | {rows:,} | {size_kb:.1f} KB | {short_cs} |"
            )

        if extra_stats:
            lines += ["", "## Pipeline Statistics", ""]
            for key, val in extra_stats.items():
                lines.append(f"- **{key}**: {val}")

        lines += [
            "",
            "## Verification",
            "",
            "Each file has a `.sha256` sidecar. Verify with:",
            "```bash",
            "sha256sum -c <file>.sha256",
            "```",
        ]

        out_path.write_text("\n".join(lines) + "\n")
        logger.info("Manifest written → %s", out_path)
        return out_path

    def log_exports(self, export_paths: dict[str, Path], run_date: date) -> Path:
        """
        Append export metadata to the cumulative exports_log.csv.

        Creates the file if it doesn't exist.
        """
        log_path = self.samples_dir / "exports_log.csv"
        fieldnames = ["run_date", "label", "filename", "rows", "size_bytes", "sha256"]

        rows = []
        for label, path in export_paths.items():
            if not path.exists():
                continue
            rows.append(
                {
                    "run_date": run_date.isoformat(),
                    "label": label,
                    "filename": path.name,
                    "rows": self._count_rows(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": self._read_checksum(path),
                }
            )

        file_exists = log_path.exists()
        with open(log_path, "a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)

        logger.info("Logged %d exports to %s", len(rows), log_path)
        return log_path

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _count_rows(path: Path) -> int:
        """Row count for CSV or Parquet files; returns 0 for unknown types."""
        try:
            if path.suffix == ".csv":
                return sum(1 for _ in open(path)) - 1  # subtract header
            if path.suffix == ".parquet":
                import pyarrow.parquet as pq

                return pq.read_metadata(path).num_rows
        except Exception:
            return 0
        return 0

    @staticmethod
    def _read_checksum(path: Path) -> str:
        """Read the checksum from the .sha256 sidecar file."""
        sha_path = path.with_suffix(path.suffix + ".sha256")
        if sha_path.exists():
            return sha_path.read_text().split()[0]
        return ""
