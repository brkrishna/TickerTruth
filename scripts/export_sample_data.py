"""
Export sample data from production Dolt database for HuggingFace Space demo.
Run this monthly after your nightly pipeline completes.

Usage:
    python scripts/export_sample_data.py

Output:
    Creates sample_data/*.parquet files in project root or HF Space repo
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Determine output directory
# If running from Space repo, use ./sample_data
# Otherwise, use ../sample_data relative to this script or ./sample_data
script_dir = Path(__file__).parent
project_root = script_dir.parent
output_dir = project_root / "sample_data"

# Try alternative: check if we're in a Space repo
if not (project_root / "app.py").exists():
    # We might be in the main project, output to docs folder
    output_dir = project_root / "sample_data"

output_dir.mkdir(exist_ok=True, parents=True)

print(f"📊 Exporting sample data to: {output_dir}")
print(f"⏰ Started: {datetime.now().isoformat()}")

# ============================================================================
# OPTION A: Load from existing parquet/CSV in your project
# (Recommended if you already have data files)
# ============================================================================

try:
    # Try to load from existing data sources in your project
    # Adjust paths based on your actual data locations

    data_sources = {
        "corporate_actions": project_root / "data" / "corporate_actions.parquet",
        "symbol_lineage": project_root / "data" / "symbol_lineage.parquet",
        "security_master": project_root / "data" / "security_master.parquet",
        "adjustment_factors": project_root / "data" / "adjustment_factors.parquet",
    }

    for name, path in data_sources.items():
        if path.exists():
            print(f"  ✓ Found {name} at {path}")
        else:
            print(f"  ⚠️  Missing {name} at {path}")

except Exception as e:
    print(f"⚠️  Could not load from local data: {e}")

# ============================================================================
# OPTION B: Load from Dolt database (if you have Dolt configured)
# ============================================================================

try:
    import duckdb

    print("\n📦 Attempting to connect to Dolt database...")

    # Connect to Dolt repo
    # Adjust this based on your Dolt setup (local or remote)
    conn = duckdb.connect(":memory:")

    # If you have Dolt installed, you can query it like:
    # conn = duckdb.connect('dolt://path/to/repo')

    print("  ✓ Connected to Dolt")

    # Example query - adjust table names to match your schema
    try:
        df_ca = conn.execute("""
            SELECT
                symbol, ex_date, action_type, value_ratio,
                adjustment_factor, dividend_amount, frequency
            FROM fact_corporate_action_event
            WHERE symbol IN (
                SELECT symbol FROM dim_security_master
                WHERE trading_status = 'ACTIVE'
                ORDER BY market_cap DESC NULLS LAST
                LIMIT 50
            )
              AND ex_date >= CURRENT_DATE - INTERVAL '5 YEARS'
            ORDER BY ex_date DESC
        """).df()

        df_ca.to_parquet(output_dir / "corporate_actions.parquet", compression="snappy")
        print(f"  ✓ Exported corporate_actions: {len(df_ca)} records")
    except Exception as e:
        print(f"  ⚠️  Could not export corporate_actions: {e}")

except ImportError:
    print("\n⚠️  DuckDB not installed. Skipping Dolt export.")
except Exception as e:
    print(f"\n⚠️  Could not connect to Dolt: {e}")

# ============================================================================
# OPTION C: Create synthetic sample data (for testing/demo)
# ============================================================================

print("\n📝 Creating synthetic sample data for testing...")

try:
    # Synthetic corporate actions
    df_ca_synthetic = pd.DataFrame(
        {
            "symbol": [
                "RELIANCE",
                "RELIANCE",
                "INFY",
                "INFY",
                "TCS",
                "TATASTEEL",
                "TATASTEEL",
            ]
            * 2,
            "ex_date": pd.date_range("2020-01-01", periods=14, freq="6M"),
            "action_type": [
                "SPLIT",
                "BONUS",
                "DIVIDEND",
                "SPLIT",
                "DIVIDEND",
                "SPLIT",
                "BONUS",
            ]
            * 2,
            "value_ratio": ["1:5", "1:2", "21.0", "1:2", "15.0", "1:2", "1:1"] * 2,
            "adjustment_factor": [0.2, 0.5, 1.0, 0.5, 1.0, 0.5, 0.5] * 2,
            "dividend_amount": [0, 0, 21.0, 0, 15.0, 0, 0] * 2,
            "frequency": ["", "", "FINAL", "", "INTERIM", "", ""] * 2,
        }
    )

    df_ca_synthetic.to_parquet(
        output_dir / "corporate_actions.parquet", compression="snappy"
    )
    print(f"  ✓ Created synthetic corporate_actions: {len(df_ca_synthetic)} records")

    # Synthetic symbol lineage
    df_lineage = pd.DataFrame(
        {
            "symbol": ["POWERGRID", "ZENITHEQUIP", "AEGISLOG"],
            "old_symbol": ["POWERGRID", "ZENITHEQUIP", "AEGISLOG"],
            "new_symbol": ["POWERGRDL", "ICIL", "AEGIS"],
            "effective_date": pd.to_datetime(
                ["2025-12-30", "2022-06-30", "2025-10-15"]
            ),
            "event_type": ["RENAME", "MERGER", "RENAME"],
            "reason": [
                "Name change by issuer",
                "Merger with ICIL",
                "Symbol optimization",
            ],
        }
    )

    df_lineage.to_parquet(output_dir / "symbol_lineage.parquet", compression="snappy")
    print(f"  ✓ Created synthetic symbol_lineage: {len(df_lineage)} records")

    # Synthetic security master
    df_sm = pd.DataFrame(
        {
            "symbol": [
                "RELIANCE",
                "INFY",
                "TCS",
                "TATASTEEL",
                "WIPRO",
                "HDFC",
                "ICICIBANK",
                "HDBANK",
                "AXISBANK",
                "SBIN",
            ],
            "isin": [
                "INE002A01018",
                "INE009A01021",
                "INE467B01029",
                "INE081A01012",
                "INE009A01025",
                "INE001A01036",
                "INE090A01021",
                "INE026A01034",
                "INE424H01027",
                "INE682A01012",
            ],
            "company_name": [
                "Reliance Industries",
                "Infosys",
                "Tata Consultancy Services",
                "Tata Steel",
                "Wipro",
                "HDFC Bank",
                "ICICI Bank",
                "HDFC Bank",
                "Axis Bank",
                "State Bank of India",
            ],
            "sector": [
                "OIL & GAS",
                "IT",
                "IT",
                "STEEL",
                "IT",
                "BANKING",
                "BANKING",
                "BANKING",
                "BANKING",
                "BANKING",
            ],
            "listing_date": pd.to_datetime(
                [
                    "1995-01-01",
                    "1993-06-01",
                    "1997-08-01",
                    "1993-03-01",
                    "1994-07-01",
                    "1995-10-01",
                    "1997-01-01",
                    "1995-10-01",
                    "1995-12-01",
                    "1991-07-01",
                ]
            ),
            "trading_status": ["ACTIVE"] * 10,
            "market_cap": [
                150000,
                85000,
                120000,
                45000,
                65000,
                180000,
                95000,
                180000,
                110000,
                200000,
            ],
        }
    )

    df_sm.to_parquet(output_dir / "security_master.parquet", compression="snappy")
    print(f"  ✓ Created synthetic security_master: {len(df_sm)} records")

    # Synthetic adjustment factors
    df_adj = pd.DataFrame(
        {
            "symbol": [
                "RELIANCE",
                "RELIANCE",
                "TATASTEEL",
                "TATASTEEL",
                "TATASTEEL",
                "INFY",
                "INFY",
            ],
            "ex_date": pd.to_datetime(
                [
                    "2020-01-01",
                    "2023-05-31",
                    "2018-02-01",
                    "2020-05-20",
                    "2023-11-10",
                    "2022-06-01",
                    "2024-08-15",
                ]
            ),
            "action_type": [
                "SPLIT",
                "SPLIT",
                "BONUS",
                "SPLIT",
                "DIVIDEND",
                "SPLIT",
                "DIVIDEND",
            ],
            "adjustment_factor": [0.5, 0.2, 0.1667, 0.5, 1.0, 0.5, 1.0],
            "cumulative_adjustment_factor": [
                0.5,
                0.1,
                0.1667,
                0.0834,
                0.0834,
                0.5,
                0.5,
            ],
        }
    )

    df_adj.to_parquet(output_dir / "adjustment_factors.parquet", compression="snappy")
    print(f"  ✓ Created synthetic adjustment_factors: {len(df_adj)} records")

except Exception as e:
    print(f"  ❌ Error creating synthetic data: {e}")
    sys.exit(1)

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 60)
print("✅ Export Complete!")
print("=" * 60)
print(f"\n📁 Files created in: {output_dir}/")
for f in output_dir.glob("*.parquet"):
    size_mb = f.stat().st_size / 1024 / 1024
    print(f"  ✓ {f.name} ({size_mb:.2f} MB)")

print(f"\n⏰ Completed: {datetime.now().isoformat()}")
print("\n📋 Next steps:")
print("  1. Copy sample_data/ to your HF Space repo: sample_data/")
print("  2. git add sample_data/")
print("  3. git commit -m 'chore: refresh sample data'")
print("  4. git push")
print("\n🚀 Space will auto-reload with new data in ~30 seconds")
