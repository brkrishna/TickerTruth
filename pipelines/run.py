"""
ICASHTL pipeline entry point.

Runs the full ETL pipeline end-to-end or any subset of tasks:

  python pipelines/run.py                          # full run, today's date
  python pipelines/run.py --date 2026-05-31        # specific date
  python pipelines/run.py --tasks extract,normalize # only those stages
  python pipelines/run.py --dry-run                # skip Dolt commit + R2
  python pipelines/run.py --no-fetch               # skip NSE downloads
  python pipelines/run.py --no-dolt-commit         # skip Dolt commit/tag

Exit codes:
  0 — all selected tasks completed without hard failures
  1 — one or more tasks failed
  2 — argument error
"""

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run")

ALL_TASKS = [
    "extract",
    "normalize",
    "lineage",
    "adjust",
    "validate",
    "load",
    "export",
    "manifest",
    "release-notes",
]


# ── task runners ──────────────────────────────────────────────────────────────

def run_extract(run_date: date, dry_run: bool) -> bool:
    """Task 5: fetch NSE symbols, bhavcopy, corporate actions → data/raw/."""
    from pipelines.extract.extractor import RawDataExtractor
    extractor = RawDataExtractor()
    ok = True

    logger.info("[extract] Fetching NSE equity master...")
    try:
        df = extractor.fetch_nse_symbols()
        logger.info("[extract] Symbols: %d rows", len(df))
    except Exception as exc:
        logger.error("[extract] fetch_nse_symbols failed: %s", exc)
        ok = False

    logger.info("[extract] Fetching bhavcopy for %s...", run_date)
    try:
        df = extractor.fetch_bhavcopy(run_date)
        logger.info("[extract] Bhavcopy: %d rows", len(df))
    except NotImplementedError:
        logger.warning("[extract] fetch_bhavcopy is a stub — skipping")
    except Exception as exc:
        logger.warning("[extract] fetch_bhavcopy failed (non-fatal): %s", exc)

    logger.info("[extract] Fetching corporate actions (last 90 days)...")
    try:
        df = extractor.fetch_nse_corporate_actions()
        logger.info("[extract] Corporate actions: %d rows", len(df))
    except NotImplementedError:
        logger.warning("[extract] fetch_nse_corporate_actions is a stub — skipping")
    except Exception as exc:
        logger.warning("[extract] fetch_nse_corporate_actions failed (non-fatal): %s", exc)

    logger.info("[extract] Consolidating to staging...")
    try:
        report = extractor.consolidate_to_staging(run_date=run_date)
        for src, stats in report.items():
            logger.info("[extract] staging.%s: %d rows", src, stats["rows_after_dedup"])
    except Exception as exc:
        logger.error("[extract] consolidate_to_staging failed: %s", exc)
        ok = False

    return ok


def run_normalize(run_date: date) -> bool:
    """Task 6: normalize staging data → data/curated/ dim and fact tables."""
    from pipelines.normalize.normalizer import RawToCanonicalMapper
    import pandas as pd

    curated_dir = PROJECT_ROOT / "data" / "curated"
    staging_dir = PROJECT_ROOT / "data" / "staging"
    curated_dir.mkdir(parents=True, exist_ok=True)

    symbols_path = staging_dir / "nse_symbols_consolidated.csv"
    actions_path = staging_dir / "nse_actions_consolidated.csv"

    if not symbols_path.exists():
        logger.warning("[normalize] nse_symbols_consolidated.csv not found — skipping")
        return True

    logger.info("[normalize] Mapping to canonical schema...")
    try:
        mapper   = RawToCanonicalMapper(source_file=symbols_path.name)
        raw_syms = pd.read_csv(symbols_path)

        dim_issuer = mapper.map_to_dim_issuer(raw_syms)
        dim_issuer.to_csv(curated_dir / "dim_issuer.csv", index=False)
        logger.info("[normalize] dim_issuer: %d rows", len(dim_issuer))

        dim_security = mapper.map_to_dim_security_master(raw_syms, dim_issuer)
        dim_security.to_csv(curated_dir / "dim_security_master.csv", index=False)
        logger.info("[normalize] dim_security_master: %d rows", len(dim_security))

        if actions_path.exists():
            raw_actions = pd.read_csv(actions_path)
            fact_ca = mapper.map_to_fact_corporate_action_event(raw_actions, dim_security)
            fact_ca.to_csv(curated_dir / "fact_corporate_action_event.csv", index=False)
            logger.info("[normalize] fact_corporate_action_event: %d rows", len(fact_ca))
        else:
            logger.warning("[normalize] nse_actions_consolidated.csv not found — skipping actions")

        return True
    except Exception as exc:
        logger.error("[normalize] failed: %s", exc)
        return False


def run_lineage(run_date: date) -> bool:
    """Task 7: detect symbol lineage events → data/curated/fact_symbol_lineage_event.csv."""
    import pandas as pd
    from pipelines.lineage.linker import SymbolLinker

    curated_dir = PROJECT_ROOT / "data" / "curated"
    sec_path    = curated_dir / "dim_security_master.csv"
    actions_path = curated_dir / "fact_corporate_action_event.csv"

    if not sec_path.exists():
        logger.warning("[lineage] dim_security_master.csv not found — skipping")
        return True

    try:
        linker   = SymbolLinker()
        security = pd.read_csv(sec_path)

        # Use active vs. all securities as the two snapshots
        current    = security[security.get("active_flag", pd.Series([True] * len(security))) == True]  # noqa: E712
        historical = security

        events = linker.link_across_periods(
            current_symbols=current.rename(columns={"nse_symbol": "SYMBOL", "isin": "ISIN"}),
            historical_symbols=historical.rename(columns={"nse_symbol": "SYMBOL", "isin": "ISIN"}),
            period_date=run_date,
        )

        if actions_path.exists():
            actions = pd.read_csv(actions_path)
            events  = linker.cross_reference_with_actions(events, actions)

        out = curated_dir / "fact_symbol_lineage_event.csv"
        events.to_csv(out, index=False)
        logger.info("[lineage] fact_symbol_lineage_event: %d rows", len(events))
        return True
    except Exception as exc:
        logger.error("[lineage] failed: %s", exc)
        return False


def run_adjust(run_date: date) -> bool:
    """Task 8: compute adjustment factors → data/curated/fact_adjustment_factor.csv."""
    import pandas as pd
    from pipelines.adjustments.adjuster import AdjustmentFactorBuilder

    curated_dir = PROJECT_ROOT / "data" / "curated"
    ca_path     = curated_dir / "fact_corporate_action_event.csv"
    sec_path    = curated_dir / "dim_security_master.csv"

    if not ca_path.exists():
        logger.warning("[adjust] fact_corporate_action_event.csv not found — skipping")
        return True

    try:
        actions  = pd.read_csv(ca_path)
        symbols  = pd.read_csv(sec_path) if sec_path.exists() else pd.DataFrame()
        builder  = AdjustmentFactorBuilder()
        factors  = builder.build_from_corporate_actions(actions, symbols)
        out      = curated_dir / "fact_adjustment_factor.csv"
        factors.to_csv(out, index=False)
        logger.info("[adjust] fact_adjustment_factor: %d rows", len(factors))
        return True
    except Exception as exc:
        logger.error("[adjust] failed: %s", exc)
        return False


def run_validate(run_date: date) -> bool:
    """Task 10: run QA checks against curated files."""
    from pipelines.publish.data_validator import DataValidator
    validator = DataValidator()
    results   = validator.run_curated_checks()
    summary   = DataValidator.summarize(results)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        logger.info("[validate] [%s] %s — %s", status, r.name, r.details)
        for err in r.errors:
            logger.warning("[validate]        %s", err)
    logger.info(
        "[validate] %d/%d checks passed", summary["passed"], summary["total"]
    )
    return summary["all_passed"]


def run_load(
    run_date: date,
    dry_run: bool,
    no_dolt_commit: bool,
    validate_passed: bool = True,
    stats: dict | None = None,
) -> bool:
    """Task 9: load curated data into Dolt, commit, and tag."""
    from pipelines.publish.dolt_importer import DoltImporter
    importer = DoltImporter()

    logger.info("[load] Importing curated files into Dolt...")
    try:
        report = importer.import_all(run_date=run_date)
        for table, tbl_stats in report["tables"].items():
            logger.info("[load] %s: %s (%d rows)", table, tbl_stats["status"], tbl_stats["rows"])
        if report["errors"]:
            for err in report["errors"]:
                logger.error("[load] %s", err)
            return False
    except Exception as exc:
        logger.error("[load] import_all failed: %s", exc)
        return False

    if not validate_passed:
        logger.warning(
            "[load] Skipping Dolt commit — validate failed. "
            "Fix data issues and re-run with --tasks load to commit."
        )
        return True

    if dry_run or no_dolt_commit:
        logger.info("[load] Skipping Dolt commit (dry-run or --no-dolt-commit)")
        return True

    tag = f"v{run_date.strftime('%Y.%m.%d')}"
    try:
        commit_hash = importer.commit(
            f"ETL import: {run_date.isoformat()}", tag=tag
        )
        logger.info("[load] Dolt commit: %s  tag: %s", commit_hash, tag)
        if stats is not None:
            stats["dolt_commit"] = commit_hash
    except Exception as exc:
        logger.error("[load] Dolt commit failed: %s", exc)
        return False

    return True


def run_export(run_date: date) -> dict:
    """Task 11: generate public and paid-tier export files."""
    from pipelines.publish.sample_generator import SampleGenerator
    gen   = SampleGenerator()
    paths = {}

    logger.info("[export] Generating public samples...")
    paths.update(gen.generate_public_samples(run_date))

    logger.info("[export] Generating tier-1 exports...")
    paths.update(gen.generate_tier1_exports(run_date))

    logger.info("[export] Generating tier-2 exports...")
    paths.update(gen.generate_tier2_exports(run_date))

    logger.info("[export] Generated %d export files", len(paths))
    return paths


def run_manifest(run_date: date, export_paths: dict) -> bool:
    """Task 11: build manifest and update exports log."""
    from pipelines.publish.manifest_builder import ManifestBuilder
    builder = ManifestBuilder()

    try:
        manifest = builder.build_manifest(export_paths, run_date)
        log      = builder.log_exports(export_paths, run_date)
        logger.info("[manifest] Written: %s", manifest)
        logger.info("[manifest] Log:     %s", log)
        return True
    except Exception as exc:
        logger.error("[manifest] failed: %s", exc)
        return False


def collect_stats(run_date: date) -> dict:
    """Read row counts from curated CSVs and quality report for release notes."""
    import json
    import pandas as pd

    curated = PROJECT_ROOT / "data" / "curated"
    staging = PROJECT_ROOT / "data" / "staging"

    def csv_rows(path: Path) -> int:
        try:
            return len(pd.read_csv(path))
        except Exception:
            return 0

    stats = {
        "new_securities":  csv_rows(curated / "dim_security_master.csv"),
        "new_actions":     csv_rows(curated / "fact_corporate_action_event.csv"),
        "lineage_events":  csv_rows(curated / "fact_symbol_lineage_event.csv"),
        "adjustment_rows": csv_rows(curated / "fact_adjustment_factor.csv"),
    }

    quality_report = staging / f"quality_report_{run_date.isoformat()}.json"
    if quality_report.exists():
        try:
            data = json.loads(quality_report.read_text())
            stats["quality_warnings"] = data.get("warnings", [])
        except Exception:
            pass

    logger.info(
        "[stats] securities=%d  actions=%d  lineage=%d  adjustments=%d  warnings=%d",
        stats["new_securities"],
        stats["new_actions"],
        stats["lineage_events"],
        stats["adjustment_rows"],
        len(stats.get("quality_warnings", [])),
    )
    return stats


def run_release_notes(run_date: date, stats: dict) -> bool:
    """Task 12: generate versioned release notes and update changelog."""
    from pipelines.publish.release_notifier import ReleaseNotifier
    notifier = ReleaseNotifier()

    try:
        path = notifier.generate_release_notes(run_date, stats)
        # docs/release-notes.md is human-curated — do not write to it from the
        # pipeline. Update it manually after reviewing the versioned release file.
        logger.info("[release-notes] Written: %s", path)
        return True
    except Exception as exc:
        logger.error("[release-notes] failed: %s", exc)
        return False


# ── argument parsing ──────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="ICASHTL pipeline orchestrator",
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Run date (default: today)",
    )
    parser.add_argument(
        "--tasks",
        metavar="TASK[,TASK...]",
        default=",".join(ALL_TASKS),
        help=(
            "Comma-separated list of tasks to run. "
            f"All tasks: {', '.join(ALL_TASKS)}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Dolt commit and R2 upload",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip NSE data downloads (use existing raw files)",
    )
    parser.add_argument(
        "--no-dolt-commit",
        action="store_true",
        help="Skip Dolt commit and tag (import data but do not commit)",
    )
    return parser.parse_args(argv)


def resolve_date(date_str: str | None) -> date:
    if not date_str:
        return date.today()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid date format '%s'. Use YYYY-MM-DD.", date_str)
        sys.exit(2)


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    args     = parse_args(argv)
    run_date = resolve_date(args.date)
    tasks    = {t.strip() for t in args.tasks.split(",") if t.strip()}

    unknown = tasks - set(ALL_TASKS)
    if unknown:
        logger.error("Unknown tasks: %s. Valid: %s", unknown, ALL_TASKS)
        return 2

    logger.info(
        "Pipeline run: date=%s  tasks=%s  dry_run=%s",
        run_date, sorted(tasks), args.dry_run,
    )

    results: dict[str, bool] = {}
    export_paths: dict       = {}
    stats: dict              = {}

    if "extract" in tasks and not args.no_fetch:
        results["extract"] = run_extract(run_date, args.dry_run)

    if "normalize" in tasks:
        results["normalize"] = run_normalize(run_date)

    if "lineage" in tasks:
        results["lineage"] = run_lineage(run_date)

    if "adjust" in tasks:
        results["adjust"] = run_adjust(run_date)

    if "validate" in tasks:
        results["validate"] = run_validate(run_date)

    if "load" in tasks:
        validate_passed = results.get("validate", True)
        results["load"] = run_load(
            run_date, args.dry_run, args.no_dolt_commit,
            validate_passed=validate_passed,
            stats=stats,
        )

    if "export" in tasks:
        export_paths = run_export(run_date)
        results["export"] = bool(export_paths)

    if "manifest" in tasks:
        results["manifest"] = run_manifest(run_date, export_paths)

    if "release-notes" in tasks:
        stats.update(collect_stats(run_date))
        results["release-notes"] = run_release_notes(run_date, stats)

    # ── summary ───────────────────────────────────────────────────────────────
    logger.info("─" * 60)
    all_ok = True
    for task, ok in results.items():
        status = "✓" if ok else "✗"
        logger.info("  %s  %s", status, task)
        if not ok:
            all_ok = False

    logger.info("─" * 60)
    if all_ok:
        logger.info("Pipeline completed successfully for %s", run_date)
        return 0
    else:
        logger.error("Pipeline finished with failures — check logs above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
