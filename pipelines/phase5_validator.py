"""
Phase 5 unit tests — packaging, access management, warehouse export, onboarding.

Run:
    pytest pipelines/phase5_validator.py -v
"""

import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).parent.parent


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 1 — BundlePackager
# ═══════════════════════════════════════════════════════════════════════════════


def _seed_samples(samples_dir: Path, run_date: date) -> None:
    """Write minimal sample files so BundlePackager has data to bundle."""
    date_str = run_date.strftime("%Y%m%d")
    (samples_dir / "public").mkdir(parents=True, exist_ok=True)
    (samples_dir / "paid_tier_1").mkdir(parents=True, exist_ok=True)
    (samples_dir / "paid_tier_2").mkdir(parents=True, exist_ok=True)

    # Public CSV
    pd.DataFrame([{"nse_symbol": "INFY", "isin": "INE009A01021"}]).to_csv(
        samples_dir / "public" / f"nse_active_securities_sample_{date_str}.csv",
        index=False,
    )
    # Tier-1 CSV
    pd.DataFrame([{"nse_symbol": "TCS"}]).to_csv(
        samples_dir / "paid_tier_1" / f"extended_nse_master_{date_str}.csv",
        index=False,
    )
    # Tier-2 parquet placeholder (write as CSV; packager just globs by extension)
    pd.DataFrame([{"security_id": 1}]).to_csv(
        samples_dir / "paid_tier_2" / f"full_security_master_{date_str}.parquet",
        index=False,
    )


class TestBundlePackagerConfig:
    def test_config_loads(self, tmp_path):
        from pipelines.publish.packager import BundlePackager

        config_path = PROJECT_ROOT / "pipelines" / "publish" / "config.yaml"
        p = BundlePackager(
            config_path=config_path,
            samples_dir=tmp_path / "samples",
            bundles_dir=tmp_path / "bundles",
        )
        assert "explorer" in p.list_tiers()
        assert "starter" in p.list_tiers()

    def test_tier_config_has_required_keys(self, tmp_path):
        from pipelines.publish.packager import BundlePackager

        config_path = PROJECT_ROOT / "pipelines" / "publish" / "config.yaml"
        p = BundlePackager(
            config_path=config_path,
            samples_dir=tmp_path / "s",
            bundles_dir=tmp_path / "b",
        )
        cfg = p.tier_config("starter")
        assert "price_inr_min" in cfg
        assert "includes_adjustments" in cfg

    def test_unknown_tier_raises(self, tmp_path):
        from pipelines.publish.packager import BundlePackager

        config_path = PROJECT_ROOT / "pipelines" / "publish" / "config.yaml"
        p = BundlePackager(
            config_path=config_path,
            samples_dir=tmp_path / "s",
            bundles_dir=tmp_path / "b",
        )
        with pytest.raises(ValueError, match="Unknown tier"):
            p.tier_config("platinum")


class TestBundlePackagerBuild:
    def _make_packager(self, tmp_path):
        from pipelines.publish.packager import BundlePackager

        return BundlePackager(
            config_path=PROJECT_ROOT / "pipelines" / "publish" / "config.yaml",
            samples_dir=tmp_path / "samples",
            bundles_dir=tmp_path / "bundles",
        )

    def test_build_explorer_creates_zip(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("explorer", date(2024, 6, 1))
        assert path.exists()
        assert path.suffix == ".zip"
        assert "explorer" in path.name

    def test_zip_contains_license(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("explorer", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            assert "LICENSE.md" in zf.namelist()

    def test_zip_contains_readme(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("starter", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            assert "README.md" in zf.namelist()

    def test_zip_contains_manifest(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("explorer", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            assert "MANIFEST.json" in zf.namelist()

    def test_manifest_has_correct_tier(self, tmp_path):
        import json

        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("starter", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            manifest = json.loads(zf.read("MANIFEST.json"))
        assert manifest["tier"] == "starter"

    def test_manifest_has_file_checksums(self, tmp_path):
        import json

        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("explorer", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            manifest = json.loads(zf.read("MANIFEST.json"))
        assert manifest["files"]
        for f in manifest["files"]:
            assert len(f["sha256"]) == 64

    def test_zip_contains_sample_queries(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("professional", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            assert "sample_queries.sql" in zf.namelist()

    def test_pro_queries_include_lineage_query(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("professional", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            queries = zf.read("sample_queries.sql").decode()
        assert "fact_symbol_lineage_event" in queries

    def test_explorer_queries_exclude_lineage_query(self, tmp_path):
        _seed_samples(tmp_path / "samples", date(2024, 6, 1))
        p = self._make_packager(tmp_path)
        path = p.build_bundle("explorer", date(2024, 6, 1))
        with zipfile.ZipFile(path) as zf:
            queries = zf.read("sample_queries.sql").decode()
        # lineage query is professional+ only
        assert "fact_symbol_lineage_event" not in queries

    def test_no_data_files_raises(self, tmp_path):
        from pipelines.publish.packager import BundlePackager

        p = BundlePackager(
            config_path=PROJECT_ROOT / "pipelines" / "publish" / "config.yaml",
            samples_dir=tmp_path / "samples",  # empty — no files
            bundles_dir=tmp_path / "bundles",
        )
        with pytest.raises(FileNotFoundError):
            p.build_bundle("explorer", date(2024, 6, 1))


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 2 — AccessManager
# ═══════════════════════════════════════════════════════════════════════════════


def _make_mgr(tmp_path):
    from pipelines.publish.access_manager import AccessManager

    return AccessManager(
        buyers_csv=tmp_path / "buyers.csv",
        download_log=tmp_path / "downloads.csv",
        config_path=PROJECT_ROOT / "pipelines" / "publish" / "config.yaml",
    )


class TestAccessManagerBuyers:
    def test_create_buyer_returns_record(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        buyer = mgr.create_buyer("Acme", "acme@test.in", "starter")
        assert buyer["buyer_id"]
        assert buyer["email"] == "acme@test.in"
        assert buyer["tier"] == "starter"
        assert buyer["status"] == "active"

    def test_create_buyer_persists_to_csv(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        mgr.create_buyer("Acme", "acme@test.in", "starter")
        buyers = mgr.list_buyers()
        assert len(buyers) == 1
        assert buyers[0]["email"] == "acme@test.in"

    def test_duplicate_email_raises(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        mgr.create_buyer("Acme", "acme@test.in", "starter")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_buyer("Acme2", "acme@test.in", "professional")

    def test_list_buyers_filters_by_tier(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        mgr.create_buyer("A", "a@x.in", "starter")
        mgr.create_buyer("B", "b@x.in", "professional")
        assert len(mgr.list_buyers(tier="starter")) == 1
        assert len(mgr.list_buyers(tier="professional")) == 1
        assert len(mgr.list_buyers()) == 2

    def test_get_buyer_by_id(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        buyer = mgr.create_buyer("Acme", "acme@x.in", "starter")
        found = mgr.get_buyer(buyer["buyer_id"])
        assert found is not None
        assert found["email"] == "acme@x.in"

    def test_get_buyer_unknown_id_returns_none(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        assert mgr.get_buyer("XXXXXXXX") is None

    def test_deactivate_buyer(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        buyer = mgr.create_buyer("Acme", "acme@x.in", "starter")
        ok = mgr.deactivate_buyer(buyer["buyer_id"])
        assert ok is True
        found = mgr.get_buyer(buyer["buyer_id"])
        assert found["status"] == "inactive"

    def test_deactivate_unknown_buyer_returns_false(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        assert mgr.deactivate_buyer("XXXXXXXX") is False

    def test_list_active_only_excludes_inactive(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        buyer = mgr.create_buyer("Acme", "acme@x.in", "starter")
        mgr.deactivate_buyer(buyer["buyer_id"])
        assert mgr.list_buyers(status="active") == []
        assert len(mgr.list_buyers(status=None)) == 1


class TestAccessManagerDownloadLog:
    def test_log_download_creates_entry(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        mgr.create_buyer("A", "a@x.in", "starter")
        buyer = mgr.list_buyers()[0]
        mgr.log_download(buyer["buyer_id"], "starter", "releases/x.zip", "https://url")
        logs = mgr.list_downloads()
        assert len(logs) == 1
        assert logs[0]["s3_key"] == "releases/x.zip"

    def test_log_has_expiry(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        mgr.create_buyer("A", "a@x.in", "starter")
        buyer = mgr.list_buyers()[0]
        record = mgr.log_download(
            buyer["buyer_id"], "starter", "k", "url", expires_hours=24
        )
        assert "expires_at" in record
        assert record["expires_at"] > record["generated_at"]

    def test_list_downloads_filters_by_buyer(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        b1 = mgr.create_buyer("A", "a@x.in", "starter")
        b2 = mgr.create_buyer("B", "b@x.in", "professional")
        mgr.log_download(b1["buyer_id"], "starter", "k1", "u1")
        mgr.log_download(b2["buyer_id"], "professional", "k2", "u2")
        assert len(mgr.list_downloads(buyer_id=b1["buyer_id"])) == 1

    def test_generate_signed_url_validates_inactive_buyer(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        buyer = mgr.create_buyer("A", "a@x.in", "starter")
        mgr.deactivate_buyer(buyer["buyer_id"])
        with pytest.raises(ValueError, match="not active"):
            mgr.generate_signed_url(buyer["buyer_id"], "some/key.zip")

    def test_generate_signed_url_requires_r2_credentials(self, tmp_path):
        import os

        mgr = _make_mgr(tmp_path)
        buyer = mgr.create_buyer("A", "a@x.in", "starter")
        # Ensure R2 env vars are absent
        for key in [
            "R2_ENDPOINT",
            "R2_BUCKET",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
        ]:
            os.environ.pop(key, None)
        with pytest.raises(RuntimeError, match="R2 credentials"):
            mgr.generate_signed_url(buyer["buyer_id"], "releases/test.zip")


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 3 — WarehouseExporter
# ═══════════════════════════════════════════════════════════════════════════════


class TestWarehouseExporter:
    def _make_exp(self, tmp_path):
        from pipelines.publish.warehouse_exporter import WarehouseExporter

        return WarehouseExporter(output_dir=tmp_path / "warehouse")

    def test_export_all_creates_directories(self, tmp_path):
        from pipelines.publish.warehouse_exporter import SUPPORTED_TARGETS

        exp = self._make_exp(tmp_path)
        exp.export_all()
        for target in SUPPORTED_TARGETS:
            assert (tmp_path / "warehouse" / target).is_dir()

    def test_export_creates_three_files(self, tmp_path):
        exp = self._make_exp(tmp_path)
        paths = exp.export("snowflake")
        assert len(paths) == 3

    def test_unknown_target_raises(self, tmp_path):
        exp = self._make_exp(tmp_path)
        with pytest.raises(ValueError, match="Unknown target"):
            exp.export("oracle")

    @pytest.mark.parametrize(
        "target", ["snowflake", "bigquery", "databricks", "duckdb"]
    )
    def test_schema_file_non_empty(self, tmp_path, target):
        exp = self._make_exp(tmp_path)
        paths = exp.export(target)
        schema = next(p for p in paths if p.name == "schema.sql")
        assert schema.stat().st_size > 200

    @pytest.mark.parametrize(
        "target", ["snowflake", "bigquery", "databricks", "duckdb"]
    )
    def test_schema_contains_core_tables(self, tmp_path, target):
        exp = self._make_exp(tmp_path)
        paths = exp.export(target)
        schema = next(p for p in paths if p.name == "schema.sql")
        content = schema.read_text()
        for table in [
            "dim_security_master",
            "fact_corporate_action_event",
            "fact_adjustment_factor",
        ]:
            assert table in content, f"{target} schema missing {table}"

    def test_snowflake_ddl_uses_autoincrement(self, tmp_path):
        exp = self._make_exp(tmp_path)
        paths = exp.export("snowflake")
        schema = next(p for p in paths if p.name == "schema.sql")
        assert "AUTOINCREMENT" in schema.read_text()

    def test_bigquery_ddl_uses_int64(self, tmp_path):
        exp = self._make_exp(tmp_path)
        paths = exp.export("bigquery")
        schema = next(p for p in paths if p.name == "schema.sql")
        assert "INT64" in schema.read_text()

    def test_databricks_ddl_uses_delta(self, tmp_path):
        exp = self._make_exp(tmp_path)
        paths = exp.export("databricks")
        schema = next(p for p in paths if p.name == "schema.sql")
        assert "USING DELTA" in schema.read_text()

    def test_duckdb_ddl_uses_references(self, tmp_path):
        exp = self._make_exp(tmp_path)
        paths = exp.export("duckdb")
        schema = next(p for p in paths if p.name == "schema.sql")
        assert "REFERENCES" in schema.read_text()

    @pytest.mark.parametrize(
        "target", ["snowflake", "bigquery", "databricks", "duckdb"]
    )
    def test_queries_file_non_empty(self, tmp_path, target):
        exp = self._make_exp(tmp_path)
        paths = exp.export(target)
        q = next(p for p in paths if p.name == "sample_queries.sql")
        assert q.stat().st_size > 100

    @pytest.mark.parametrize(
        "target", ["snowflake", "bigquery", "databricks", "duckdb"]
    )
    def test_field_catalog_has_adjustment_factor_docs(self, tmp_path, target):
        exp = self._make_exp(tmp_path)
        paths = exp.export(target)
        cat = next(p for p in paths if p.name == "field_catalog.md")
        assert "total_adjustment_factor" in cat.read_text()


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 4 — Onboarding Docs
# ═══════════════════════════════════════════════════════════════════════════════

ONBOARDING_PATH = PROJECT_ROOT / "docs" / "onboarding.md"

REQUIRED_SECTIONS = [
    "Receiving a New Inquiry",
    "Sending the Explorer Sample",
    "Creating a Buyer Record",
    "Payment Collection",
    "Delivering the Bundle",
    "Monthly Renewal Delivery",
    "Access Revocation",
    "Audit Trail",
]

REQUIRED_COMMANDS = [
    "access_manager",
    "packager",
    "generate_signed_url",
    "deactivate_buyer",
    "download_log",
]


class TestOnboardingDocs:
    def test_onboarding_exists(self):
        assert ONBOARDING_PATH.exists()

    def test_onboarding_not_empty(self):
        assert ONBOARDING_PATH.stat().st_size > 1000

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, section):
        content = ONBOARDING_PATH.read_text()
        assert section in content, f"Onboarding missing section: {section!r}"

    @pytest.mark.parametrize("cmd", REQUIRED_COMMANDS)
    def test_mentions_required_command(self, cmd):
        content = ONBOARDING_PATH.read_text()
        assert cmd in content, f"Onboarding doesn't mention: {cmd!r}"

    def test_has_code_blocks(self):
        assert "```" in ONBOARDING_PATH.read_text()

    def test_mentions_razorpay(self):
        content = ONBOARDING_PATH.read_text().lower()
        assert "razorpay" in content

    def test_mentions_r2(self):
        assert "R2" in ONBOARDING_PATH.read_text()
