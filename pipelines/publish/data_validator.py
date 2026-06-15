"""
DataValidator — QA checks for Phase 3.

Two modes:
  1. Curated-file checks (pandas only, no Dolt needed) — run after normalization
  2. Post-import checks (requires live Dolt)              — run after DoltImporter

All check methods return a CheckResult namedtuple so tests can assert
on individual fields without parsing strings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from pipelines.publish.dolt_importer import DoltImporter

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CURATED_DIR = PROJECT_ROOT / "data" / "curated"


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str = ""
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.passed


class DataValidator:
    """
    Runs data quality checks against curated CSV files and/or Dolt.

    Usage:
        validator = DataValidator()

        # Check curated files (no Dolt needed)
        results = validator.run_curated_checks()

        # Check Dolt post-import (requires live Dolt)
        results = validator.run_dolt_checks()
    """

    def __init__(
        self,
        curated_dir: Path = CURATED_DIR,
        dolt_importer: DoltImporter | None = None,
    ):
        self.curated_dir = Path(curated_dir)
        self._dolt = dolt_importer  # injected; None = Dolt checks unavailable

    # ── curated-file checks (no Dolt needed) ─────────────────────────────────

    def check_required_files_exist(self) -> CheckResult:
        """Verify all expected curated CSV files are present and non-empty.

        Core files (dim tables from equity master) must always be present.
        Fact files that depend on NSE corporate actions API are optional — missing
        them is a warning, not a hard failure, when the upstream API is unreachable.
        """
        core_files = [
            "dim_issuer.csv",
            "dim_security_master.csv",
        ]
        optional_files = [
            "fact_corporate_action_event.csv",
            "fact_adjustment_factor.csv",
            "fact_symbol_lineage_event.csv",
        ]
        missing_core = []
        empty_core = []
        missing_opt = []

        for fname in core_files:
            path = self.curated_dir / fname
            if not path.exists():
                missing_core.append(fname)
            elif path.stat().st_size == 0:
                empty_core.append(fname)

        for fname in optional_files:
            path = self.curated_dir / fname
            if not path.exists():
                missing_opt.append(fname)

        errors = [f"missing: {f}" for f in missing_core] + [
            f"empty: {f}" for f in empty_core
        ]
        warnings = [f"missing: {f}" for f in missing_opt]
        passed = not errors
        total = len(core_files) + len(optional_files)
        present = total - len(missing_core) - len(empty_core) - len(missing_opt)
        details = f"{present}/{total} files present and non-empty"
        if warnings:
            details += f" ({len(missing_opt)} optional fact file(s) absent — upstream data unavailable)"
        return CheckResult(
            name="required_files_exist",
            passed=passed,
            details=details,
            errors=errors + warnings,
        )

    def check_primary_keys_unique(self) -> CheckResult:
        """Verify no duplicate PKs in dimension and fact tables."""
        pk_map = {
            "dim_issuer.csv": "issuer_id",
            "dim_security_master.csv": "security_id",
            "fact_adjustment_factor.csv": None,  # composite PK checked separately
        }
        errors = []
        for fname, pk_col in pk_map.items():
            path = self.curated_dir / fname
            if not path.exists():
                continue
            df = pd.read_csv(path)
            if pk_col and pk_col in df.columns:
                dupes = df[pk_col].duplicated().sum()
                if dupes:
                    errors.append(f"{fname}: {dupes} duplicate {pk_col} values")

        # Composite PK check for fact_adjustment_factor
        adj_path = self.curated_dir / "fact_adjustment_factor.csv"
        if adj_path.exists():
            df = pd.read_csv(adj_path)
            if "security_id" in df.columns and "as_of_date" in df.columns:
                dupes = df.duplicated(subset=["security_id", "as_of_date"]).sum()
                if dupes:
                    errors.append(
                        f"fact_adjustment_factor.csv: {dupes} duplicate (security_id, as_of_date)"
                    )

        return CheckResult(
            name="primary_keys_unique",
            passed=not errors,
            details="No duplicate PKs"
            if not errors
            else f"{len(errors)} PK violation(s)",
            errors=errors,
        )

    def check_referential_integrity(self) -> CheckResult:
        """
        Verify all security_ids in fact tables exist in dim_security_master.
        """
        master_path = self.curated_dir / "dim_security_master.csv"
        if not master_path.exists():
            return CheckResult(
                name="referential_integrity",
                passed=False,
                details="dim_security_master.csv not found",
                errors=["dim_security_master.csv missing"],
            )

        master_ids = set(pd.read_csv(master_path)["security_id"].dropna())
        errors = []

        for fname in [
            "fact_corporate_action_event.csv",
            "fact_adjustment_factor.csv",
            "fact_symbol_lineage_event.csv",
            "fact_listing_status_history.csv",
        ]:
            path = self.curated_dir / fname
            if not path.exists():
                continue
            df = pd.read_csv(path)
            if "security_id" not in df.columns:
                continue
            orphans = set(df["security_id"].dropna()) - master_ids
            if orphans:
                errors.append(
                    f"{fname}: {len(orphans)} security_ids not in dim_security_master"
                    f" (e.g. {list(orphans)[:3]})"
                )

        return CheckResult(
            name="referential_integrity",
            passed=not errors,
            details="All FK security_ids resolve"
            if not errors
            else f"{len(errors)} FK violation(s)",
            errors=errors,
        )

    def check_adjustment_factors_valid(self) -> CheckResult:
        """
        Verify all adjustment factors are in (0, 1000].
        Split/bonus factors should be < 1 for normal splits.
        """
        path = self.curated_dir / "fact_adjustment_factor.csv"
        if not path.exists():
            return CheckResult(
                name="adjustment_factors_valid",
                passed=True,
                details="fact_adjustment_factor.csv not found — skipping",
            )

        df = pd.read_csv(path)
        errors = []
        for col in [
            "cumulative_split_adjustment",
            "cumulative_bonus_adjustment",
            "total_adjustment_factor",
        ]:
            if col not in df.columns:
                continue
            non_positive = (df[col] <= 0).sum()
            extreme = (df[col] > 1000).sum()
            if non_positive:
                errors.append(f"{col}: {non_positive} non-positive values")
            if extreme:
                errors.append(f"{col}: {extreme} values > 1000 (likely data error)")

        return CheckResult(
            name="adjustment_factors_valid",
            passed=not errors,
            details=f"{len(df)} adjustment rows checked",
            errors=errors,
        )

    def check_lineage_events_valid(self) -> CheckResult:
        """
        Verify lineage events have valid confidence scores and no self-loops.
        """
        path = self.curated_dir / "fact_symbol_lineage_event.csv"
        if not path.exists():
            return CheckResult(
                name="lineage_events_valid",
                passed=True,
                details="fact_symbol_lineage_event.csv not found — skipping",
            )

        df = pd.read_csv(path)
        errors = []

        if "confidence" in df.columns:
            out_of_range = ((df["confidence"] < 0) | (df["confidence"] > 1)).sum()
            if out_of_range:
                errors.append(f"{out_of_range} confidence values outside [0, 1]")

        if "symbol_from" in df.columns and "symbol_to" in df.columns:
            self_loops = (
                df["symbol_from"].notna()
                & df["symbol_to"].notna()
                & (df["symbol_from"] == df["symbol_to"])
            ).sum()
            if self_loops:
                errors.append(f"{self_loops} self-loop lineage events (from == to)")

        if "event_date" in df.columns:
            null_dates = df["event_date"].isna().sum()
            if null_dates:
                errors.append(f"{null_dates} rows have null event_date")

        return CheckResult(
            name="lineage_events_valid",
            passed=not errors,
            details=f"{len(df)} lineage events checked",
            errors=errors,
        )

    def check_confidence_scores(self) -> CheckResult:
        """
        Check confidence score distribution across fact_corporate_action_event.
        Warns if > 20% of rows have confidence < 0.7 (manual review threshold).
        """
        path = self.curated_dir / "fact_corporate_action_event.csv"
        if not path.exists():
            return CheckResult(
                name="confidence_scores",
                passed=True,
                details="fact_corporate_action_event.csv not found — skipping",
            )

        df = pd.read_csv(path)
        errors = []

        if "confidence_score" not in df.columns:
            return CheckResult(
                name="confidence_scores",
                passed=True,
                details="No confidence_score column present",
            )

        total = len(df)
        low_conf = (df["confidence_score"] < 0.7).sum()
        low_conf_pct = low_conf / total if total > 0 else 0

        if low_conf_pct > 0.20:
            errors.append(
                f"{low_conf_pct:.1%} of corporate action rows have confidence < 0.7 "
                f"({low_conf}/{total}) — check extraction quality"
            )

        return CheckResult(
            name="confidence_scores",
            passed=not errors,
            details=f"Low-confidence rows: {low_conf}/{total} ({low_conf_pct:.1%})",
            errors=errors,
        )

    # ── BSE-specific curated checks ───────────────────────────────────────────

    def check_bse_files_exist(self) -> CheckResult:
        """Verify expected BSE curated files are present and non-empty."""
        core_files = ["dim_bse_scrip_master.csv"]
        optional_files = [
            "fact_bse_scrip_lineage_event.csv",
            "fact_exchange_security_map.csv",
            "bse_fact_adjustment_factor.csv",
        ]
        missing_core = []
        empty_core = []
        missing_opt = []

        for fname in core_files:
            path = self.curated_dir / fname
            if not path.exists():
                missing_core.append(fname)
            elif path.stat().st_size == 0:
                empty_core.append(fname)

        for fname in optional_files:
            path = self.curated_dir / fname
            if not path.exists():
                missing_opt.append(fname)

        errors = [f"missing: {f}" for f in missing_core] + [
            f"empty: {f}" for f in empty_core
        ]
        warnings = [f"optional missing: {f}" for f in missing_opt]
        total = len(core_files) + len(optional_files)
        present = total - len(missing_core) - len(empty_core) - len(missing_opt)
        return CheckResult(
            name="bse_files_exist",
            passed=not errors,
            details=f"{present}/{total} BSE files present",
            errors=errors + warnings,
        )

    def check_bse_scrip_codes_valid(self) -> CheckResult:
        """Verify all BSE scrip codes are 6-digit zero-padded strings."""
        path = self.curated_dir / "dim_bse_scrip_master.csv"
        if not path.exists():
            return CheckResult(
                name="bse_scrip_codes_valid",
                passed=True,
                details="dim_bse_scrip_master.csv not found — skipping",
            )

        df = pd.read_csv(path, dtype={"scrip_code": str})
        errors = []

        if "scrip_code" not in df.columns:
            return CheckResult(
                name="bse_scrip_codes_valid",
                passed=False,
                details="scrip_code column missing",
                errors=["scrip_code column not found in dim_bse_scrip_master.csv"],
            )

        invalid = df["scrip_code"].dropna()
        non_six_digit = invalid[~invalid.str.match(r"^\d{6}$")]
        if len(non_six_digit):
            errors.append(
                f"{len(non_six_digit)} scrip codes not exactly 6 digits "
                f"(e.g. {non_six_digit.head(3).tolist()})"
            )

        null_codes = df["scrip_code"].isna().sum()
        if null_codes:
            errors.append(f"{null_codes} rows have null scrip_code")

        return CheckResult(
            name="bse_scrip_codes_valid",
            passed=not errors,
            details=f"{len(df)} scrip codes validated",
            errors=errors,
        )

    def check_bse_adjustment_factors_valid(self) -> CheckResult:
        """Verify BSE adjustment factors are in (0, 1000]."""
        path = self.curated_dir / "bse_fact_adjustment_factor.csv"
        if not path.exists():
            return CheckResult(
                name="bse_adjustment_factors_valid",
                passed=True,
                details="bse_fact_adjustment_factor.csv not found — skipping",
            )

        df = pd.read_csv(path)
        errors = []
        for col in [
            "cumulative_split_adjustment",
            "cumulative_bonus_adjustment",
            "total_adjustment_factor",
        ]:
            if col not in df.columns:
                continue
            non_positive = (df[col] <= 0).sum()
            extreme = (df[col] > 1000).sum()
            if non_positive:
                errors.append(f"BSE {col}: {non_positive} non-positive values")
            if extreme:
                errors.append(f"BSE {col}: {extreme} values > 1000 (likely data error)")

        return CheckResult(
            name="bse_adjustment_factors_valid",
            passed=not errors,
            details=f"{len(df)} BSE adjustment rows checked",
            errors=errors,
        )

    def check_isin_bridge_integrity(self) -> CheckResult:
        """
        Verify every ISIN in fact_exchange_security_map appears in at least
        one of NSE dim_security_master or BSE dim_bse_scrip_master.
        """
        bridge_path = self.curated_dir / "fact_exchange_security_map.csv"
        if not bridge_path.exists():
            return CheckResult(
                name="isin_bridge_integrity",
                passed=True,
                details="fact_exchange_security_map.csv not found — skipping",
            )

        bridge = pd.read_csv(bridge_path)
        if "isin" not in bridge.columns:
            return CheckResult(
                name="isin_bridge_integrity",
                passed=False,
                errors=["isin column missing from fact_exchange_security_map.csv"],
            )

        nse_path = self.curated_dir / "dim_security_master.csv"
        bse_path = self.curated_dir / "dim_bse_scrip_master.csv"

        known_isins: set[str] = set()
        for path, col in [(nse_path, "isin"), (bse_path, "isin")]:
            if path.exists():
                df = pd.read_csv(path)
                if col in df.columns:
                    known_isins.update(df[col].dropna().astype(str).str.upper())

        bridge_isins = set(bridge["isin"].dropna().astype(str).str.upper())
        orphan_isins = bridge_isins - known_isins
        errors = []
        if orphan_isins:
            errors.append(
                f"{len(orphan_isins)} ISINs in bridge not found in any security master "
                f"(e.g. {list(orphan_isins)[:3]})"
            )

        dual_listed = (
            (bridge["is_bse_only"].eq(False) & bridge["is_nse_only"].eq(False)).sum()
            if "is_bse_only" in bridge.columns and "is_nse_only" in bridge.columns
            else 0
        )

        return CheckResult(
            name="isin_bridge_integrity",
            passed=not errors,
            details=f"{len(bridge_isins)} bridge ISINs checked; {dual_listed} dual-listed",
            errors=errors,
        )

    def run_bse_checks(self) -> list[CheckResult]:
        """Run all BSE-specific curated-file checks and return results."""
        checks = [
            self.check_bse_files_exist,
            self.check_bse_scrip_codes_valid,
            self.check_bse_adjustment_factors_valid,
            self.check_isin_bridge_integrity,
        ]
        results = []
        for fn in checks:
            try:
                result = fn()
                status = "PASS" if result.passed else "FAIL"
                logger.info("[%s] %s — %s", status, result.name, result.details)
                results.append(result)
            except Exception as exc:
                logger.error("BSE check %s raised: %s", fn.__name__, exc)
                results.append(
                    CheckResult(name=fn.__name__, passed=False, errors=[str(exc)])
                )
        return results

    def run_curated_checks(self) -> list[CheckResult]:
        """Run all curated-file checks and return results."""
        checks = [
            self.check_required_files_exist,
            self.check_primary_keys_unique,
            self.check_referential_integrity,
            self.check_adjustment_factors_valid,
            self.check_lineage_events_valid,
            self.check_confidence_scores,
        ]
        results = []
        for fn in checks:
            try:
                result = fn()
                status = "PASS" if result.passed else "FAIL"
                logger.info("[%s] %s — %s", status, result.name, result.details)
                results.append(result)
            except Exception as exc:
                logger.error("Check %s raised: %s", fn.__name__, exc)
                results.append(
                    CheckResult(
                        name=fn.__name__,
                        passed=False,
                        errors=[str(exc)],
                    )
                )
        return results

    # ── post-import Dolt checks ───────────────────────────────────────────────

    def check_dolt_row_counts(self, expected: dict[str, int]) -> CheckResult:
        """
        Compare Dolt table row counts to expected values.

        Args:
            expected: {table_name: expected_row_count}
        """
        if self._dolt is None:
            return CheckResult(
                name="dolt_row_counts",
                passed=False,
                errors=["DoltImporter not provided — cannot run Dolt checks"],
            )

        actual = self._dolt.get_table_counts()
        errors = []
        for table, exp_count in expected.items():
            act_count = actual.get(table, -1)
            if act_count < 0:
                errors.append(f"{table}: query failed")
            elif act_count < exp_count:
                errors.append(f"{table}: expected ≥ {exp_count} rows, got {act_count}")

        return CheckResult(
            name="dolt_row_counts",
            passed=not errors,
            details=f"Checked {len(expected)} tables",
            errors=errors,
        )

    def check_dolt_no_orphan_facts(self) -> CheckResult:
        """
        Run a SQL query to find fact rows with no matching dim_security_master entry.
        """
        if self._dolt is None:
            return CheckResult(
                name="dolt_no_orphan_facts",
                passed=False,
                errors=["DoltImporter not provided"],
            )

        queries = {
            "fact_corporate_action_event": (
                "SELECT COUNT(*) as n FROM fact_corporate_action_event f "
                "LEFT JOIN dim_security_master d ON f.security_id = d.security_id "
                "WHERE d.security_id IS NULL"
            ),
            "fact_adjustment_factor": (
                "SELECT COUNT(*) as n FROM fact_adjustment_factor f "
                "LEFT JOIN dim_security_master d ON f.security_id = d.security_id "
                "WHERE d.security_id IS NULL"
            ),
        }
        errors = []
        for table, query in queries.items():
            try:
                rows = self._dolt._sql_json(query)
                orphans = int(rows[0]["n"]) if rows else 0
                if orphans:
                    errors.append(
                        f"{table}: {orphans} orphan rows (no matching security_id)"
                    )
            except Exception as exc:
                errors.append(f"{table}: query failed — {exc}")

        return CheckResult(
            name="dolt_no_orphan_facts",
            passed=not errors,
            details="No orphan fact rows"
            if not errors
            else f"{len(errors)} tables have orphans",
            errors=errors,
        )

    def run_dolt_checks(
        self, expected_counts: dict[str, int] | None = None
    ) -> list[CheckResult]:
        """Run all post-import Dolt checks."""
        results = [self.check_dolt_no_orphan_facts()]
        if expected_counts:
            results.append(self.check_dolt_row_counts(expected_counts))
        return results

    # ── summary helpers ───────────────────────────────────────────────────────

    @staticmethod
    def summarize(results: list[CheckResult]) -> dict:
        passed = sum(1 for r in results if r.passed)
        return {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "all_passed": passed == len(results),
        }
