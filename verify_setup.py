#!/usr/bin/env python3
"""
Phase 1 setup verification script.
Validates:
1. Python environment (.venv, requirements.txt, dependencies)
2. Dolt repo initialized and schema committed
3. Directory and file structure matches Phase 1 tasks
4. Website config and docs scaffold in place
5. Pipeline YAML configs present
"""

import sys
import subprocess
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────


def _run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=10)


def _check_files(label, paths, require_nonempty=False):
    """Check a list of paths exist (and optionally are non-empty). Returns (passed, failed)."""
    failed = []
    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            print(f"  ✗ {p}: NOT FOUND")
            failed.append(p)
        elif require_nonempty and path.stat().st_size == 0:
            print(f"  ✗ {p}: EXISTS BUT EMPTY")
            failed.append(p)
        else:
            size = path.stat().st_size
            print(f"  ✓ {p} ({size:,} bytes)")
    return len(failed) == 0, failed


def _check_dirs(paths):
    failed = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            print(f"  ✓ {p}/")
        else:
            print(f"  ✗ {p}/: NOT FOUND")
            failed.append(p)
    return len(failed) == 0, failed


# ── checks ───────────────────────────────────────────────────────────────────


def check_venv_and_requirements():
    """Verify .venv and requirements.txt exist."""
    print("Checking Python environment...")
    ok, _ = _check_files(
        "environment", [".venv/bin/activate", "requirements.txt"], require_nonempty=True
    )
    if ok:
        print("  ✓ PASS: venv and requirements.txt present")
    return ok


def check_python_dependencies():
    """Verify all packages from requirements.txt are importable."""
    print("Checking Python dependencies...")

    packages = {
        "pandas": "data manipulation",
        "numpy": "numerical operations",
        "pyarrow": "Parquet support",
        "requests": "HTTP downloads",
        "bs4": "HTML scraping (beautifulsoup4)",
        "sqlalchemy": "database ORM",
        "dotenv": "env variable loading (python-dotenv)",
        "pytest": "test runner",
    }

    failed = []
    for pkg, desc in packages.items():
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}: {desc}")
        except ImportError:
            print(f"  ✗ {pkg}: NOT INSTALLED ({desc})")
            failed.append(pkg)

    if failed:
        print(f"\n  Install missing: pip install {' '.join(failed)}")
        return False

    print("  ✓ PASS: All dependencies installed")
    return True


def check_dolt_repo():
    """Verify Dolt is installed, repo initialized, and schema committed."""
    print("Checking Dolt repo...")

    try:
        r = _run(["dolt", "version"])
        if r.returncode != 0:
            print("  ✗ FAIL: dolt command not working")
            return False
        print(f"  ✓ dolt binary: {r.stdout.decode().strip()}")
    except FileNotFoundError:
        print("  ✗ FAIL: 'dolt' not found. Install: brew install dolt")
        return False

    if not Path("dolt/.dolt").is_dir():
        print("  ✗ FAIL: dolt/.dolt not found. Run: cd dolt && dolt init")
        return False

    # dolt ls lists tables (replaces the invalid 'dolt tables' command)
    r = _run(["dolt", "ls"], cwd="dolt")
    if r.returncode != 0:
        print(f"  ✗ FAIL: dolt ls failed: {r.stderr.decode().strip()}")
        return False
    tables = [
        line.strip()
        for line in r.stdout.decode().splitlines()
        if line.strip() and "Tables" not in line
    ]
    print(
        f"  ✓ {len(tables)} tables in working set: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}"
    )

    # Verify schema has been committed (not just initialized)
    r = _run(["dolt", "log", "--oneline"], cwd="dolt")
    commits = [line for line in r.stdout.decode().splitlines() if line.strip()]
    if len(commits) < 2:
        print(
            "  ✗ FAIL: Schema not committed. Run: cd dolt && dolt add -A && dolt commit -m 'schema: initial'"
        )
        return False
    print(f"  ✓ {len(commits)} commits in Dolt history (versioned baseline exists)")

    print("  ✓ PASS: Dolt repo initialized and schema committed")
    return True


def check_directory_structure():
    """Verify all required directories exist."""
    print("Checking directory structure...")

    dirs = [
        "pipelines/extract",
        "pipelines/normalize",
        "pipelines/lineage",
        "pipelines/adjustments",
        "pipelines/publish",
        "dolt",
        "data/raw",
        "data/staging",
        "data/curated",
        "data/samples",
        "docs",
        "website/landing-page",
        "releases",
        "tests",
    ]
    ok, _ = _check_dirs(dirs)
    if ok:
        print("  ✓ PASS: All directories present")
    return ok


def check_schema_and_seed_files():
    """Verify Dolt schema and seed files exist and are non-empty."""
    print("Checking schema and seed files...")

    files = [
        "dolt/schema.sql",
        "dolt/seed_corporate_actions.sql",
        "dolt/drop_tables.sql",
    ]
    ok, _ = _check_files("dolt files", files, require_nonempty=True)
    if ok:
        print("  ✓ PASS: Schema and seed files present")
    return ok


def check_pipeline_configs():
    """Verify pipeline YAML configs and key source files exist."""
    print("Checking pipeline config files...")

    files = [
        "pipelines/extract/sources.yaml",
        "pipelines/normalize/field_mappings.yaml",
        "pipelines/lineage/rules.yaml",
        "pipelines/adjustments/rules.yaml",
    ]
    ok, _ = _check_files("pipeline configs", files, require_nonempty=True)
    if ok:
        print("  ✓ PASS: Pipeline config files present")
    return ok


def check_docs_and_website():
    """Verify docs scaffold and website config exist and are non-empty."""
    print("Checking docs and website scaffold...")

    passed = True

    # docs/ files must have content
    docs_files = [
        "docs/methodology.md",
        "docs/product-overview.md",
        "docs/pricing.md",
        "docs/release-notes.md",
        "docs/sample-queries.md",
        "docs/source-inventory.md",
    ]
    ok, _ = _check_files("docs/", docs_files, require_nonempty=True)
    passed = passed and ok

    # website config must exist and be non-empty
    website_cfg = ["website/config.yaml"]
    ok, _ = _check_files("website config", website_cfg, require_nonempty=True)
    passed = passed and ok

    # landing-page files must exist; warn if empty (content optional at scaffold stage)
    lp_files = [
        "website/landing-page/index.md",
        "website/landing-page/methodology.md",
        "website/landing-page/pricing.md",
        "website/landing-page/product-overview.md",
        "website/landing-page/release-notes.md",
        "website/landing-page/sample-queries.md",
    ]
    print("  Landing-page files (warn if empty):")
    empty = []
    for p in lp_files:
        path = Path(p)
        if not path.exists():
            print(f"  ✗ {p}: NOT FOUND")
            passed = False
        elif path.stat().st_size == 0:
            print(f"  ⚠ {p}: empty — needs content before site can deploy")
            empty.append(p)
        else:
            print(f"  ✓ {p} ({path.stat().st_size:,} bytes)")
    if empty:
        print(
            f"  ⚠ WARN: {len(empty)} landing-page file(s) are empty. Copy content from docs/ before deploying."
        )

    if passed:
        print("  ✓ PASS: Docs and website scaffold in place")
    return passed


# ── main ─────────────────────────────────────────────────────────────────────


def main():
    print("\n" + "=" * 60)
    print("TickerTruth Phase 1 Setup Verification")
    print("=" * 60 + "\n")

    checks = [
        ("Python environment", check_venv_and_requirements),
        ("Python dependencies", check_python_dependencies),
        ("Dolt repo", check_dolt_repo),
        ("Directory structure", check_directory_structure),
        ("Schema & seed files", check_schema_and_seed_files),
        ("Pipeline configs", check_pipeline_configs),
        ("Docs & website", check_docs_and_website),
    ]

    results = []
    for name, fn in checks:
        try:
            result = fn()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append((name, False))
        print()

    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, r in results:
        mark = "✅" if r else "❌"
        print(f"  {mark} {name}")

    print()
    if all(r for _, r in results):
        print(f"✅ All checks passed ({passed}/{total}) — Phase 1 complete\n")
        return 0
    else:
        print(f"❌ {total - passed} check(s) failed ({passed}/{total})\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
