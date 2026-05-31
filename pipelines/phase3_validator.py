"""
Phase 3 unit tests — Dolt integration, QA, export, release notes.

Run all tests:
    pytest pipelines/phase3_validator.py -v

Tests use tmp_path fixtures and mock subprocess calls so they run
without a live Dolt instance or pre-existing curated files.
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 1 — DoltImporter
# ═══════════════════════════════════════════════════════════════════════════════

class TestDoltImporterColumnFilter:
    """filter_to_schema drops quality/provenance columns before import."""

    def test_filter_keeps_declared_columns(self):
        from pipelines.publish.dolt_importer import DoltImporter
        df = pd.DataFrame([{
            "security_id": 1, "nse_symbol": "INFY", "isin": "INE009A01021",
            "company_name": "INFOSYS LIMITED", "issuer_id": 1, "exchange_id": 1,
            "listing_date": "1993-06-03", "active_flag": True,
            "_source_file": "test.csv",     # quality col — must be dropped
            "_quality_issues": "",          # quality col — must be dropped
            "_confidence_score": 1.0,       # quality col — must be dropped
        }])
        result = DoltImporter.filter_to_schema(df, "dim_security_master")
        assert "_source_file"    not in result.columns
        assert "_quality_issues" not in result.columns
        assert "nse_symbol"      in result.columns
        assert "active_flag"     in result.columns

    def test_filter_returns_only_schema_columns(self):
        from pipelines.publish.dolt_importer import DoltImporter, _TABLE_COLUMNS
        df = pd.DataFrame([{
            "security_id": 1, "nse_symbol": "INFY", "isin": "INE009A01021",
            "company_name": "X", "issuer_id": 1, "exchange_id": 1,
            "listing_date": "2024-01-01", "active_flag": True,
            "extra_col": "should_be_dropped",
        }])
        result = DoltImporter.filter_to_schema(df, "dim_security_master")
        declared = set(_TABLE_COLUMNS["dim_security_master"])
        assert set(result.columns) <= declared

    def test_filter_unknown_table_returns_empty(self):
        from pipelines.publish.dolt_importer import DoltImporter
        df     = pd.DataFrame([{"a": 1, "b": 2}])
        result = DoltImporter.filter_to_schema(df, "nonexistent_table")
        assert len(result.columns) == 0


class TestDoltImporterResolveActionTypes:
    """resolve_action_type_ids maps action_code → action_type_id from Dolt."""

    def _make_importer_with_mock(self, action_map: dict):
        from pipelines.publish.dolt_importer import DoltImporter
        imp = DoltImporter.__new__(DoltImporter)
        imp.dolt_dir    = Path("/tmp/dolt")
        imp.curated_dir = Path("/tmp/curated")
        imp.get_action_type_map = MagicMock(return_value=action_map)
        return imp

    def test_known_codes_resolved(self):
        imp = self._make_importer_with_mock({"BONUS": 2, "SPLIT": 3, "DIVIDEND": 1})
        df  = pd.DataFrame([
            {"action_code": "BONUS",    "event_date": "2024-01-01"},
            {"action_code": "SPLIT",    "event_date": "2024-02-01"},
            {"action_code": "DIVIDEND", "event_date": "2024-03-01"},
        ])
        result = imp.resolve_action_type_ids(df)
        assert list(result["action_type_id"]) == [2, 3, 1]

    def test_unknown_codes_dropped(self):
        imp = self._make_importer_with_mock({"BONUS": 2})
        df  = pd.DataFrame([
            {"action_code": "BONUS",   "event_date": "2024-01-01"},
            {"action_code": "UNKNOWN", "event_date": "2024-02-01"},
        ])
        result = imp.resolve_action_type_ids(df)
        assert len(result) == 1
        assert result.iloc[0]["action_type_id"] == 2

    def test_empty_action_map_raises(self):
        from pipelines.publish.dolt_importer import DoltImporter
        imp = self._make_importer_with_mock({})
        df  = pd.DataFrame([{"action_code": "BONUS"}])
        with pytest.raises(RuntimeError, match="dim_corporate_action_type is empty"):
            imp.resolve_action_type_ids(df)


class TestDoltImporterImportOrder:
    """import_all skips missing files and respects table ordering."""

    def test_import_all_skips_missing_curated_files(self, tmp_path):
        from pipelines.publish.dolt_importer import DoltImporter

        imp = DoltImporter.__new__(DoltImporter)
        imp.dolt_dir    = tmp_path / "dolt"
        imp.curated_dir = tmp_path / "curated"
        imp.curated_dir.mkdir()

        # Mock internal helpers so no real subprocess runs
        imp.ensure_exchange_seeded = MagicMock()
        imp.get_action_type_map    = MagicMock(return_value={"BONUS": 1})
        imp.load_table             = MagicMock(return_value=5)

        report = imp.import_all(run_date=date(2024, 6, 1))

        # All tables should be skipped (no CSV files created)
        assert all(
            v["status"] == "skipped"
            for v in report["tables"].values()
        )

    def test_import_all_loads_existing_file(self, tmp_path):
        from pipelines.publish.dolt_importer import DoltImporter

        curated = tmp_path / "curated"
        curated.mkdir()
        pd.DataFrame([{
            "issuer_id": 1, "issuer_name": "INFOSYS LIMITED",
            "sector": "IT", "market_cap_category": None, "country": "India",
        }]).to_csv(curated / "dim_issuer.csv", index=False)

        imp = DoltImporter.__new__(DoltImporter)
        imp.dolt_dir    = tmp_path / "dolt"
        imp.curated_dir = curated
        imp.ensure_exchange_seeded = MagicMock()
        imp.get_action_type_map    = MagicMock(return_value={})
        imp.load_table             = MagicMock(return_value=1)

        report = imp.import_all(run_date=date(2024, 6, 1))
        assert report["tables"]["dim_issuer"]["status"] == "ok"
        assert report["tables"]["dim_issuer"]["rows"]   == 1


class TestDoltImporterCommit:
    """commit() stages, commits, and returns a hash."""

    def _make_imp(self, dolt_dir):
        from pipelines.publish.dolt_importer import DoltImporter
        imp = DoltImporter.__new__(DoltImporter)
        imp.dolt_dir    = dolt_dir
        imp.curated_dir = dolt_dir
        return imp

    def test_commit_calls_add_and_commit(self, tmp_path):
        imp = self._make_imp(tmp_path)
        run_calls = []

        def fake_run(args, **kwargs):
            run_calls.append(args)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "abc123 initial commit\n" if args[0] == "log" else ""
            r.stderr = ""
            return r

        imp._run = fake_run
        imp.commit("Test commit")

        assert any(a[0] == "add" for a in run_calls), "dolt add not called"
        assert any(a[0] == "commit" for a in run_calls), "dolt commit not called"

    def test_commit_creates_tag_when_given(self, tmp_path):
        imp = self._make_imp(tmp_path)
        tag_called = []

        def fake_run(args, **kwargs):
            if args[0] == "tag":
                tag_called.append(args)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "abc123 msg\n" if args[0] == "log" else ""
            r.stderr = ""
            return r

        imp._run = fake_run
        imp.commit("Test commit", tag="v20240601")
        assert tag_called, "dolt tag not called"
        assert "v20240601" in tag_called[0]

    def test_nothing_to_commit_returns_empty_string(self, tmp_path):
        imp = self._make_imp(tmp_path)

        def fake_run(args, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = "nothing to commit"
            r.stderr = "nothing to commit"
            return r

        imp._run = fake_run
        result = imp.commit("Empty commit")
        assert result == ""


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 2 — DataValidator
# ═══════════════════════════════════════════════════════════════════════════════

def _write_curated(tmp_path, name, df):
    path = tmp_path / name
    df.to_csv(path, index=False)
    return path


class TestDataValidatorCuratedChecks:

    def _make_validator(self, tmp_path):
        from pipelines.publish.data_validator import DataValidator
        return DataValidator(curated_dir=tmp_path)

    def test_required_files_all_present(self, tmp_path):
        from pipelines.publish.data_validator import DataValidator
        # Write minimal curated files
        required = [
            "dim_issuer.csv", "dim_security_master.csv",
            "fact_corporate_action_event.csv",
            "fact_adjustment_factor.csv", "fact_symbol_lineage_event.csv",
        ]
        for fname in required:
            pd.DataFrame([{"col": "val"}]).to_csv(tmp_path / fname, index=False)

        v = DataValidator(curated_dir=tmp_path)
        result = v.check_required_files_exist()
        assert result.passed

    def test_required_files_missing(self, tmp_path):
        v = self._make_validator(tmp_path)
        result = v.check_required_files_exist()
        assert not result.passed
        assert result.errors

    def test_primary_keys_unique_pass(self, tmp_path):
        _write_curated(tmp_path, "dim_security_master.csv", pd.DataFrame([
            {"security_id": 1, "nse_symbol": "INFY"},
            {"security_id": 2, "nse_symbol": "TCS"},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_primary_keys_unique()
        assert result.passed

    def test_primary_keys_duplicate_fails(self, tmp_path):
        _write_curated(tmp_path, "dim_security_master.csv", pd.DataFrame([
            {"security_id": 1, "nse_symbol": "INFY"},
            {"security_id": 1, "nse_symbol": "TCS"},   # duplicate PK
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_primary_keys_unique()
        assert not result.passed

    def test_referential_integrity_pass(self, tmp_path):
        _write_curated(tmp_path, "dim_security_master.csv", pd.DataFrame([
            {"security_id": 1}, {"security_id": 2},
        ]))
        _write_curated(tmp_path, "fact_adjustment_factor.csv", pd.DataFrame([
            {"security_id": 1, "as_of_date": "2024-01-01", "total_adjustment_factor": 0.5},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_referential_integrity()
        assert result.passed

    def test_referential_integrity_orphan_fails(self, tmp_path):
        _write_curated(tmp_path, "dim_security_master.csv", pd.DataFrame([
            {"security_id": 1},
        ]))
        _write_curated(tmp_path, "fact_adjustment_factor.csv", pd.DataFrame([
            {"security_id": 99, "as_of_date": "2024-01-01", "total_adjustment_factor": 0.5},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_referential_integrity()
        assert not result.passed
        assert "99" in str(result.errors)

    def test_adjustment_factors_valid(self, tmp_path):
        _write_curated(tmp_path, "fact_adjustment_factor.csv", pd.DataFrame([
            {"security_id": 1, "as_of_date": "2024-01-01",
             "cumulative_split_adjustment": 0.5,
             "cumulative_bonus_adjustment": 1.0,
             "total_adjustment_factor": 0.5},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_adjustment_factors_valid()
        assert result.passed

    def test_adjustment_factors_zero_fails(self, tmp_path):
        _write_curated(tmp_path, "fact_adjustment_factor.csv", pd.DataFrame([
            {"security_id": 1, "as_of_date": "2024-01-01",
             "cumulative_split_adjustment": 0.0,    # invalid!
             "total_adjustment_factor": 0.0},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_adjustment_factors_valid()
        assert not result.passed

    def test_lineage_events_valid(self, tmp_path):
        _write_curated(tmp_path, "fact_symbol_lineage_event.csv", pd.DataFrame([
            {"symbol_from": "OLD", "symbol_to": "NEW",
             "event_date": "2024-01-01", "confidence": 0.95},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_lineage_events_valid()
        assert result.passed

    def test_lineage_self_loop_fails(self, tmp_path):
        _write_curated(tmp_path, "fact_symbol_lineage_event.csv", pd.DataFrame([
            {"symbol_from": "SAME", "symbol_to": "SAME",    # self-loop!
             "event_date": "2024-01-01", "confidence": 0.90},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_lineage_events_valid()
        assert not result.passed

    def test_confidence_scores_all_high(self, tmp_path):
        _write_curated(tmp_path, "fact_corporate_action_event.csv", pd.DataFrame([
            {"security_id": 1, "action_code": "BONUS",
             "event_date": "2024-01-01", "confidence_score": 0.95},
            {"security_id": 2, "action_code": "SPLIT",
             "event_date": "2024-02-01", "confidence_score": 0.90},
        ]))
        v = self._make_validator(tmp_path)
        result = v.check_confidence_scores()
        assert result.passed

    def test_confidence_scores_mostly_low_fails(self, tmp_path):
        rows = [{"security_id": i, "action_code": "BONUS",
                 "event_date": "2024-01-01", "confidence_score": 0.50}
                for i in range(10)]
        _write_curated(tmp_path, "fact_corporate_action_event.csv", pd.DataFrame(rows))
        v = self._make_validator(tmp_path)
        result = v.check_confidence_scores()
        assert not result.passed   # > 20% low confidence

    def test_summarize_counts_correctly(self):
        from pipelines.publish.data_validator import DataValidator, CheckResult
        results = [
            CheckResult("a", True),
            CheckResult("b", False, errors=["bad"]),
            CheckResult("c", True),
        ]
        summary = DataValidator.summarize(results)
        assert summary["total"]      == 3
        assert summary["passed"]     == 2
        assert summary["failed"]     == 1
        assert summary["all_passed"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 3 — SampleGenerator + ManifestBuilder
# ═══════════════════════════════════════════════════════════════════════════════

class TestSampleGenerator:

    def _seed_curated(self, curated_dir):
        """Write minimal curated CSVs for sample generation tests."""
        pd.DataFrame([
            {"security_id": i, "nse_symbol": f"SYM{i}", "isin": f"INE{i:09d}",
             "company_name": f"Company {i}", "sector": "IT",
             "listing_date": "2000-01-01", "active_flag": True}
            for i in range(1, 151)
        ]).to_csv(curated_dir / "dim_security_master.csv", index=False)

        pd.DataFrame([
            {"security_id": i, "action_code": "BONUS", "event_date": "2024-01-01",
             "old_value": 1.0, "confidence_score": 0.95}
            for i in range(1, 151)
        ]).to_csv(curated_dir / "fact_corporate_action_event.csv", index=False)

        pd.DataFrame([
            {"security_id": i, "as_of_date": "2024-01-01",
             "cumulative_split_adjustment": 0.5,
             "cumulative_bonus_adjustment": 0.5,
             "cumulative_dividend_adjustment": 1.0,
             "total_adjustment_factor": 0.25}
            for i in range(1, 11)
        ]).to_csv(curated_dir / "fact_adjustment_factor.csv", index=False)

        pd.DataFrame([
            {"security_id": i, "symbol_from": f"OLD{i}", "symbol_to": f"SYM{i}",
             "event_date": "2024-01-01", "confidence": 0.9}
            for i in range(1, 6)
        ]).to_csv(curated_dir / "fact_symbol_lineage_event.csv", index=False)

    def test_public_samples_creates_files(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator, PUBLIC_SAMPLE_SIZE
        curated = tmp_path / "curated"
        curated.mkdir()
        self._seed_curated(curated)
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_public_samples(date(2024, 6, 1))
        assert "securities_sample" in paths
        assert paths["securities_sample"].exists()

    def test_public_sample_respects_size_limit(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator, PUBLIC_SAMPLE_SIZE
        curated = tmp_path / "curated"
        curated.mkdir()
        self._seed_curated(curated)
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_public_samples(date(2024, 6, 1))
        df    = pd.read_csv(paths["securities_sample"])
        assert len(df) <= PUBLIC_SAMPLE_SIZE

    def test_public_sample_has_checksum_file(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        curated = tmp_path / "curated"
        curated.mkdir()
        self._seed_curated(curated)
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_public_samples(date(2024, 6, 1))
        for path in paths.values():
            sha_path = path.with_suffix(path.suffix + ".sha256")
            assert sha_path.exists(), f"Missing checksum: {sha_path}"

    def test_compute_checksum_deterministic(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        f = tmp_path / "test.csv"
        f.write_text("a,b\n1,2\n")
        cs1 = SampleGenerator.compute_checksum(f)
        cs2 = SampleGenerator.compute_checksum(f)
        assert cs1 == cs2
        assert len(cs1) == 64   # SHA-256 hex

    def test_checksum_changes_with_content(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        f = tmp_path / "test.csv"
        f.write_text("a,b\n1,2\n")
        cs1 = SampleGenerator.compute_checksum(f)
        f.write_text("a,b\n1,3\n")   # changed
        cs2 = SampleGenerator.compute_checksum(f)
        assert cs1 != cs2

    def test_tier1_exports_creates_parquet(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        curated = tmp_path / "curated"
        curated.mkdir()
        self._seed_curated(curated)
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_tier1_exports(date(2024, 6, 1))
        for key in ["extended_master", "corp_actions_3yr", "adjustment_factors"]:
            assert key in paths, f"Missing key: {key}"
            assert paths[key].exists()

    def test_tier2_exports_full_history(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        curated = tmp_path / "curated"
        curated.mkdir()
        self._seed_curated(curated)
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_tier2_exports(date(2024, 6, 1))
        assert len(paths) >= 3   # at least securities, actions, adjustments

    def test_parquet_row_count_preserved(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        import pyarrow.parquet as pq
        curated = tmp_path / "curated"
        curated.mkdir()
        self._seed_curated(curated)
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_tier1_exports(date(2024, 6, 1))
        adj   = paths.get("adjustment_factors")
        if adj and adj.exists():
            meta = pq.read_metadata(adj)
            assert meta.num_rows == 10   # 10 rows seeded

    def test_generate_skips_missing_curated_file(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        curated = tmp_path / "curated"
        curated.mkdir()
        # Don't create dim_security_master.csv
        gen   = SampleGenerator(curated_dir=curated, samples_dir=tmp_path / "samples")
        paths = gen.generate_public_samples(date(2024, 6, 1))
        assert "securities_sample" not in paths   # skipped gracefully


class TestManifestBuilder:

    def _make_export_files(self, tmp_path):
        from pipelines.publish.sample_generator import SampleGenerator
        f = tmp_path / "test_export.csv"
        pd.DataFrame([{"a": 1, "b": 2}]).to_csv(f, index=False)
        SampleGenerator._write_parquet.__func__(None, pd.DataFrame([{"a": 1}]),
                                                tmp_path / "test.parquet") if False else None
        # Just write a plain CSV with a checksum
        cs = SampleGenerator.compute_checksum(f)
        (f.with_suffix(".csv.sha256")).write_text(f"{cs}  {f.name}\n")
        return {"test_export": f}

    def test_build_manifest_creates_file(self, tmp_path):
        from pipelines.publish.manifest_builder import ManifestBuilder
        builder = ManifestBuilder(samples_dir=tmp_path)
        files   = self._make_export_files(tmp_path)
        path    = builder.build_manifest(files, date(2024, 6, 1))
        assert path.exists()
        assert path.suffix == ".md"

    def test_manifest_contains_date(self, tmp_path):
        from pipelines.publish.manifest_builder import ManifestBuilder
        builder = ManifestBuilder(samples_dir=tmp_path)
        files   = self._make_export_files(tmp_path)
        path    = builder.build_manifest(files, date(2024, 6, 1))
        content = path.read_text()
        assert "2024-06-01" in content

    def test_manifest_contains_filename(self, tmp_path):
        from pipelines.publish.manifest_builder import ManifestBuilder
        builder = ManifestBuilder(samples_dir=tmp_path)
        files   = self._make_export_files(tmp_path)
        path    = builder.build_manifest(files, date(2024, 6, 1))
        content = path.read_text()
        assert "test_export.csv" in content

    def test_log_exports_creates_csv(self, tmp_path):
        from pipelines.publish.manifest_builder import ManifestBuilder
        builder = ManifestBuilder(samples_dir=tmp_path)
        files   = self._make_export_files(tmp_path)
        log     = builder.log_exports(files, date(2024, 6, 1))
        assert log.exists()
        df = pd.read_csv(log)
        assert len(df) == 1
        assert df.iloc[0]["label"] == "test_export"

    def test_log_exports_appends(self, tmp_path):
        from pipelines.publish.manifest_builder import ManifestBuilder
        builder = ManifestBuilder(samples_dir=tmp_path)
        files   = self._make_export_files(tmp_path)
        builder.log_exports(files, date(2024, 6, 1))
        builder.log_exports(files, date(2024, 7, 1))
        df = pd.read_csv(tmp_path / "exports_log.csv")
        assert len(df) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 4 — ReleaseNotifier
# ═══════════════════════════════════════════════════════════════════════════════

class TestReleaseNotifier:

    def test_generate_release_notes_creates_file(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=tmp_path / "changelog.md",
        )
        stats = {"new_securities": 10, "new_actions": 50, "lineage_events": 5}
        path  = notifier.generate_release_notes(date(2024, 6, 1), stats)
        assert path.exists()
        assert path.name == "v2024.06.01.md"

    def test_release_notes_contains_version(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=tmp_path / "changelog.md",
        )
        path    = notifier.generate_release_notes(date(2024, 6, 1), {})
        content = path.read_text()
        assert "v2024.06.01" in content

    def test_release_notes_includes_stats(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=tmp_path / "changelog.md",
        )
        stats   = {"new_securities": 42, "new_actions": 150, "lineage_events": 7}
        path    = notifier.generate_release_notes(date(2024, 6, 1), stats)
        content = path.read_text()
        assert "42" in content
        assert "150" in content
        assert "7" in content

    def test_release_notes_includes_warnings(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=tmp_path / "changelog.md",
        )
        stats = {"quality_warnings": ["12% low-confidence rows in actions"]}
        path  = notifier.generate_release_notes(date(2024, 6, 1), stats)
        assert "12% low-confidence" in path.read_text()

    def test_update_changelog_creates_file(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        cl = tmp_path / "release-notes.md"
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=cl,
        )
        notifier.update_changelog(date(2024, 6, 1), {"new_actions": 50})
        assert cl.exists()
        assert "2024-06-01" in cl.read_text()

    def test_update_changelog_prepends_to_existing(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        cl = tmp_path / "release-notes.md"
        cl.write_text("# Release Notes\n\n### v2024.05.01 — old entry\n")
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=cl,
        )
        notifier.update_changelog(date(2024, 6, 1), {"new_actions": 10})
        content = cl.read_text()
        # New entry should appear before old entry
        assert content.index("2024-06-01") < content.index("2024.05.01")

    def test_multiple_releases_accumulate(self, tmp_path):
        from pipelines.publish.release_notifier import ReleaseNotifier
        cl = tmp_path / "release-notes.md"
        notifier = ReleaseNotifier(
            releases_dir=tmp_path / "releases",
            changelog=cl,
        )
        notifier.update_changelog(date(2024, 5, 1), {"new_actions": 30})
        notifier.update_changelog(date(2024, 6, 1), {"new_actions": 50})
        content = cl.read_text()
        assert "2024-05-01" in content
        assert "2024-06-01" in content
