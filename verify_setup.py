#!/usr/bin/env python3
"""
Lightweight setup verification script.
Validates:
1. Dolt repo initializes successfully
2. Python dependencies can be imported
3. Docs files exist and are readable
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dolt_repo():
    """Verify Dolt repo is initialized."""
    print("✓ Checking Dolt repo...")
    dolt_dir = Path("dolt/.dolt")
    
    if not dolt_dir.exists():
        print("  ✗ FAIL: .dolt/ not found. Run: cd dolt && dolt init")
        return False
    
    try:
        result = subprocess.run(
            ["dolt", "tables"],
            cwd="dolt",
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            tables = result.stdout.decode().strip().split('\n')
            print(f"  ✓ PASS: Dolt repo initialized ({len(tables)} tables)")
            return True
        else:
            print(f"  ✗ FAIL: dolt command failed: {result.stderr.decode()}")
            return False
    except FileNotFoundError:
        print("  ✗ FAIL: 'dolt' command not found. Install Dolt: brew install dolt")
        return False


def check_python_dependencies():
    """Verify key Python dependencies are installed."""
    print("✓ Checking Python dependencies...")
    
    required_packages = {
        'pandas': 'Data manipulation',
        'pyarrow': 'Parquet file support',
        'requests': 'HTTP downloads',
    }
    
    failed = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"  ✓ {package}: {description}")
        except ImportError:
            print(f"  ✗ {package}: NOT INSTALLED ({description})")
            failed.append(package)
    
    if failed:
        print(f"\n  Install missing: pip install {' '.join(failed)}")
        return False
    
    print("  ✓ PASS: All core dependencies installed")
    return True


def check_docs_files():
    """Verify documentation files exist and are readable."""
    print("✓ Checking documentation files...")
    
    required_docs = [
        "README.md",
        "docs/methodology.md",
        "docs/product-overview.md",
        "data/README.md",
        "dolt/schema.sql",
        "pipelines/README.md",
    ]
    
    failed = []
    for doc in required_docs:
        path = Path(doc)
        if path.exists() and path.is_file():
            size = path.stat().st_size
            print(f"  ✓ {doc} ({size:,} bytes)")
        else:
            print(f"  ✗ {doc}: NOT FOUND")
            failed.append(doc)
    
    if failed:
        return False
    
    print("  ✓ PASS: All documentation files present")
    return True


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("ICASHTL Setup Verification")
    print("=" * 60 + "\n")
    
    checks = [
        check_dolt_repo,
        check_python_dependencies,
        check_docs_files,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"  ✗ ERROR: {e}\n")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ All checks passed ({passed}/{total})\n")
        return 0
    else:
        print(f"❌ {total - passed} check(s) failed ({passed}/{total})\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())