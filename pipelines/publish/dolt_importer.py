"""
DoltImporter — loads curated CSV files into the Dolt versioned database,
then commits and optionally tags the release.

Dependency order (FK constraints):
  Dims first:  dim_exchange → dim_corporate_action_type → dim_issuer
               → dim_security_master → dim_symbol_alias
  Facts after: fact_corporate_action_event → fact_adjustment_factor
               → fact_symbol_lineage_event → fact_listing_status_history
               → fact_equity_eod

fact_corporate_action_event requires action_type_id (FK) but curated CSVs
carry action_code strings.  _resolve_action_type_ids() does the lookup
from Dolt before import.
"""

import json
import logging
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DOLT_DIR     = PROJECT_ROOT / "dolt"
CURATED_DIR  = PROJECT_ROOT / "data" / "curated"

# NSE exchange seed row (inserted if dim_exchange is empty)
_NSE_EXCHANGE_ROW = {
    "exchange_id":   1,
    "exchange_code": "NSE",
    "exchange_name": "National Stock Exchange of India",
    "country":       "India",
}

# Tables and the subset of CSV columns each Dolt table accepts.
# Columns not listed here are quality/provenance metadata and must be dropped.
_TABLE_COLUMNS: dict[str, list[str]] = {
    "dim_exchange": [
        "exchange_id", "exchange_code", "exchange_name", "country",
    ],
    "dim_corporate_action_type": [
        "action_type_id", "action_code", "action_name", "description",
    ],
    "dim_issuer": [
        "issuer_id", "issuer_name", "sector", "market_cap_category", "country",
    ],
    "dim_security_master": [
        "security_id", "nse_symbol", "isin", "company_name",
        "issuer_id", "exchange_id", "listing_date", "active_flag",
    ],
    "dim_symbol_alias": [
        "alias_id", "security_id", "symbol", "alias_type",
        "effective_from", "effective_to",
    ],
    "fact_corporate_action_event": [
        "security_id", "action_type_id", "event_date", "record_date",
        "payment_date", "old_value", "new_value", "adjustment_factor",
        "description", "source", "confidence_score",
    ],
    "fact_adjustment_factor": [
        "security_id", "as_of_date",
        "cumulative_split_adjustment", "cumulative_bonus_adjustment",
        "cumulative_dividend_adjustment", "total_adjustment_factor",
    ],
    "fact_symbol_lineage_event": [
        "security_id", "old_symbol", "new_symbol",
        "change_date", "change_reason", "merged_with_symbol", "source",
    ],
    "fact_listing_status_history": [
        "security_id", "status", "effective_date", "reason",
    ],
    "fact_equity_eod": [
        "security_id", "trading_date",
        "open_price", "high_price", "low_price", "close_price", "volume",
    ],
}

# Maps lineage pipeline event_type values → fact_symbol_lineage_event.change_reason ENUM.
# LISTING and SUSPENSION have no ENUM equivalent and are skipped at import time.
_LINEAGE_EVENT_TYPE_MAP: dict[str, str] = {
    "RENAME":       "rename",
    "MERGER":       "merger",
    "DEMERGER":     "merger",   # no demerger variant in current ENUM
    "DELISTING":    "delisting",
    "RELISTING":    "relisting",
    "REACTIVATION": "relisting",
    # LISTING and SUSPENSION intentionally absent — rows are dropped with a warning
}

# Import order respects FK dependencies
_IMPORT_ORDER = [
    "dim_exchange",
    "dim_corporate_action_type",
    "dim_issuer",
    "dim_security_master",
    "dim_symbol_alias",
    "fact_corporate_action_event",
    "fact_adjustment_factor",
    "fact_symbol_lineage_event",
    "fact_listing_status_history",
    "fact_equity_eod",
]


class DoltImporter:
    """
    Loads curated CSV data into Dolt and manages commits/tags.

    Usage:
        importer = DoltImporter()
        report   = importer.import_all(run_date=date.today())
        importer.commit(f"ETL import: {date.today()}", tag=f"v{date.today():%Y%m%d}")
    """

    def __init__(
        self,
        dolt_dir: Path = DOLT_DIR,
        curated_dir: Path = CURATED_DIR,
    ):
        self.dolt_dir    = Path(dolt_dir)
        self.curated_dir = Path(curated_dir)

    # ── subprocess helpers ────────────────────────────────────────────────────

    def _run(self, args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["dolt"] + args,
            cwd=self.dolt_dir,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=120,
        )

    def _sql(self, query: str) -> str:
        """Run a SQL query and return stdout (table-formatted)."""
        result = self._run(["sql", "-q", query])
        if result.returncode != 0:
            raise RuntimeError(f"Dolt SQL failed: {result.stderr.strip()}\nQuery: {query}")
        return result.stdout

    def _sql_json(self, query: str) -> list[dict]:
        """Run a SQL query and return results as a list of dicts (JSON format)."""
        result = self._run(["sql", "-r", "json", "-q", query])
        if result.returncode != 0:
            raise RuntimeError(f"Dolt SQL failed: {result.stderr.strip()}\nQuery: {query}")
        try:
            parsed = json.loads(result.stdout)
            return parsed.get("rows", [])
        except (json.JSONDecodeError, KeyError):
            return []

    # ── exchange seed ─────────────────────────────────────────────────────────

    def ensure_exchange_seeded(self) -> None:
        """Insert NSE into dim_exchange if not already present."""
        rows = self._sql_json("SELECT exchange_id FROM dim_exchange WHERE exchange_id = 1")
        if rows:
            return
        self._sql(
            "INSERT INTO dim_exchange "
            "(exchange_id, exchange_code, exchange_name, country) VALUES "
            "(1, 'NSE', 'National Stock Exchange of India', 'India')"
        )
        logger.info("Seeded dim_exchange with NSE (exchange_id=1)")

    # ── action type seed ──────────────────────────────────────────────────────

    def ensure_action_types_seeded(self) -> None:
        """Seed dim_corporate_action_type from seed_corporate_actions.sql if empty."""
        rows = self._sql_json("SELECT COUNT(*) AS n FROM dim_corporate_action_type")
        if rows and int(rows[0].get("n", 0)) > 0:
            return
        seed_file = DOLT_DIR / "seed_corporate_actions.sql"
        result = self._run(["sql"], input_text=seed_file.read_text())
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to seed dim_corporate_action_type: {result.stderr.strip()}"
            )
        logger.info("Seeded dim_corporate_action_type from %s", seed_file.name)

    # ── action type ID resolution ─────────────────────────────────────────────

    def get_action_type_map(self) -> dict[str, int]:
        """
        Query Dolt for action_code → action_type_id mapping.
        Returns empty dict if dim_corporate_action_type is empty.
        """
        rows = self._sql_json(
            "SELECT action_type_id, action_code FROM dim_corporate_action_type"
        )
        return {r["action_code"]: int(r["action_type_id"]) for r in rows}

    def resolve_action_type_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map action_code strings → action_type_id integers using Dolt lookup.

        Rows where action_code has no mapping are dropped (logged as warnings).
        """
        action_map = self.get_action_type_map()
        if not action_map:
            raise RuntimeError(
                "dim_corporate_action_type is empty in Dolt. "
                "Load seed data before importing fact_corporate_action_event."
            )
        df = df.copy()
        df["action_type_id"] = df["action_code"].map(action_map)
        unresolved = df["action_type_id"].isna().sum()
        if unresolved:
            logger.warning(
                "%d rows have unresolvable action_code — dropping before import", unresolved
            )
            df = df.dropna(subset=["action_type_id"])
        df["action_type_id"] = df["action_type_id"].astype(int)
        return df

    # ── lineage transform ─────────────────────────────────────────────────────

    def _get_symbol_id_map(self) -> dict[str, int]:
        """Query Dolt for uppercase(nse_symbol) → security_id mapping."""
        rows = self._sql_json(
            "SELECT security_id, nse_symbol FROM dim_security_master"
        )
        return {r["nse_symbol"].upper(): int(r["security_id"]) for r in rows}

    def transform_lineage_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map lineage pipeline output to the fact_symbol_lineage_event Dolt schema.

        Lineage pipeline produces:
            symbol_from, symbol_to, event_date, event_type,
            confidence, reason, corroborating_evidence

        Dolt schema expects:
            security_id, old_symbol, new_symbol, change_date,
            change_reason, merged_with_symbol, source

        Steps:
          1. Rename columns to match Dolt schema.
          2. Map event_type → change_reason ENUM (drop unmappable types).
          3. Join dim_security_master on old_symbol (or new_symbol for relistings)
             to resolve security_id; drop rows that don't resolve.
          4. Set merged_with_symbol = new_symbol for merger rows.
          5. Set source = 'lineage_pipeline'.

        Returns a DataFrame ready for load_table(); empty if nothing survives.
        """
        if df.empty:
            return df.copy()

        df = df.copy()

        # 1. Rename
        df = df.rename(columns={
            "symbol_from": "old_symbol",
            "symbol_to":   "new_symbol",
            "event_date":  "change_date",
            "event_type":  "change_reason",
        })

        # 2. Map to ENUM values; drop rows whose event_type has no mapping
        df.loc[:, "change_reason"] = df["change_reason"].str.upper().map(_LINEAGE_EVENT_TYPE_MAP)
        n_unmappable = df["change_reason"].isna().sum()
        if n_unmappable:
            logger.warning(
                "%d lineage rows have event_type not in Dolt ENUM "
                "(LISTING / SUSPENSION) — skipping", n_unmappable
            )
            df = df[df["change_reason"].notna()].copy()

        if df.empty:
            return df

        # 3. Resolve security_id
        try:
            sym_to_id = self._get_symbol_id_map()
        except Exception as exc:
            logger.warning(
                "Could not query dim_security_master for security_id resolution: %s "
                "— lineage import skipped", exc
            )
            return df.iloc[0:0]  # empty with same columns

        def _resolve(row: pd.Series) -> int | None:
            for sym in (row.get("old_symbol"), row.get("new_symbol")):
                if sym and str(sym).upper() != "NAN":
                    sid = sym_to_id.get(str(sym).upper())
                    if sid is not None:
                        return sid
            return None

        df.loc[:, "security_id"] = df.apply(_resolve, axis=1)
        n_unresolved = df["security_id"].isna().sum()
        if n_unresolved:
            logger.warning(
                "%d lineage rows could not resolve security_id "
                "(symbol not in dim_security_master) — skipping", n_unresolved
            )
            df = df[df["security_id"].notna()].copy()

        if df.empty:
            return df

        df.loc[:, "security_id"] = df["security_id"].astype(int)

        # 4. merged_with_symbol — for merger events, new_symbol is the absorbing entity
        df.loc[:, "merged_with_symbol"] = None
        merger_mask = df["change_reason"] == "merger"
        df.loc[merger_mask, "merged_with_symbol"] = df.loc[merger_mask, "new_symbol"]

        # 5. Source tag
        df.loc[:, "source"] = "lineage_pipeline"

        # 6. Drop pipeline-internal columns not in the Dolt schema
        drop_cols = [
            c for c in ("confidence", "reason", "corroborating_evidence",
                        "corroborated", "manual_review_required")
            if c in df.columns
        ]
        if drop_cols:
            df = df.drop(columns=drop_cols)

        return df

    # ── table import ──────────────────────────────────────────────────────────

    def load_table(self, table_name: str, df: pd.DataFrame) -> int:
        """
        Load a DataFrame into a Dolt table using `dolt table import -u`.

        Filters df to only the columns declared in _TABLE_COLUMNS.
        Writes a temp CSV and calls dolt table import.

        Returns:
            Number of rows imported.

        Raises:
            RuntimeError if dolt table import fails.
        """
        declared_cols = _TABLE_COLUMNS.get(table_name, [])
        present_cols  = [c for c in declared_cols if c in df.columns]
        if not present_cols:
            raise ValueError(
                f"No declared columns found in df for table '{table_name}'. "
                f"Expected: {declared_cols}. Got: {list(df.columns)}"
            )
        subset = df[present_cols].copy()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as tmp:
            subset.to_csv(tmp, index=False)
            tmp_path = Path(tmp.name)

        try:
            result = self._run(
                ["table", "import", "-u", "--continue", table_name, str(tmp_path)]
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"dolt table import failed for '{table_name}':\n{result.stderr}"
                )
            logger.info("Loaded %d rows into %s", len(subset), table_name)
            return len(subset)
        finally:
            tmp_path.unlink(missing_ok=True)

    # ── full import orchestration ─────────────────────────────────────────────

    def import_all(self, run_date: date | None = None) -> dict:
        """
        Load all curated CSV files into Dolt in dependency order.

        Skips tables whose curated CSV does not exist.
        Returns a report dict with per-table row counts and any errors.

        Args:
            run_date: Date to use for logging; defaults to today.
        """
        run_date = run_date or date.today()
        report: dict = {"run_date": run_date.isoformat(), "tables": {}, "errors": []}

        # Always ensure static lookup tables are seeded before fact imports
        try:
            self.ensure_exchange_seeded()
        except Exception as exc:
            report["errors"].append(f"ensure_exchange_seeded: {exc}")

        try:
            self.ensure_action_types_seeded()
        except Exception as exc:
            report["errors"].append(f"ensure_action_types_seeded: {exc}")

        for table in _IMPORT_ORDER:
            csv_path = self.curated_dir / f"{table}.csv"
            if not csv_path.exists():
                logger.info("Skipping %s — curated file not found", table)
                report["tables"][table] = {"status": "skipped", "rows": 0}
                continue

            try:
                df = pd.read_csv(csv_path)

                # Special handling: resolve action_type_id FK for fact table
                if table == "fact_corporate_action_event" and "action_code" in df.columns:
                    df = self.resolve_action_type_ids(df)

                # Special handling: map lineage pipeline column names to Dolt schema
                if table == "fact_symbol_lineage_event":
                    df = self.transform_lineage_events(df)
                    if df.empty:
                        logger.info(
                            "Skipping fact_symbol_lineage_event — "
                            "no rows survived transform"
                        )
                        report["tables"][table] = {"status": "skipped", "rows": 0}
                        continue

                rows = self.load_table(table, df)
                report["tables"][table] = {"status": "ok", "rows": rows}

            except Exception as exc:
                logger.error("Failed to import %s: %s", table, exc)
                report["tables"][table] = {"status": "error", "rows": 0, "error": str(exc)}
                report["errors"].append(f"{table}: {exc}")

        return report

    # ── commit and tag ────────────────────────────────────────────────────────

    def commit(self, message: str, tag: str | None = None) -> str:
        """
        Stage all Dolt changes, commit with message, and optionally tag.

        Returns the new Dolt commit hash.
        """
        self._run(["add", "--all"])
        result = self._run(["commit", "-m", message])
        if result.returncode != 0:
            combined = result.stdout.lower() + result.stderr.lower()
            if "nothing to commit" in combined or "no changes added to commit" in combined:
                logger.info("Dolt: nothing to commit")
                return ""
            raise RuntimeError(f"dolt commit failed: {result.stderr}")

        if tag:
            tag_result = self._run(["tag", tag])
            if tag_result.returncode != 0:
                logger.warning("dolt tag failed (may already exist): %s", tag_result.stderr)

        # Return new commit hash
        log_result = self._run(["log", "--oneline", "-n", "1"])
        commit_hash = log_result.stdout.strip().split()[0] if log_result.stdout.strip() else ""
        logger.info("Dolt commit: %s  tag: %s", commit_hash, tag or "none")
        return commit_hash

    def get_table_counts(self) -> dict[str, int]:
        """Return {table_name: row_count} for all known tables."""
        counts = {}
        for table in _IMPORT_ORDER:
            try:
                rows = self._sql_json(f"SELECT COUNT(*) as n FROM {table}")
                counts[table] = int(rows[0]["n"]) if rows else 0
            except Exception:
                counts[table] = -1   # -1 = query failed
        return counts

    def rollback(self, commit_hash: str) -> None:
        """Hard-reset the Dolt working tree to a previous commit."""
        result = self._run(["reset", "--hard", commit_hash])
        if result.returncode != 0:
            raise RuntimeError(f"dolt reset failed: {result.stderr}")
        logger.warning("Rolled back to Dolt commit %s", commit_hash)

    @staticmethod
    def filter_to_schema(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """
        Return a copy of df with only the columns declared for table_name.
        Useful for testing column selection logic without a live Dolt instance.
        """
        declared = _TABLE_COLUMNS.get(table_name, [])
        present  = [c for c in declared if c in df.columns]
        return df[present].copy()
