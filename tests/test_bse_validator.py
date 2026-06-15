"""
Tests for BSE-specific checks in pipelines/publish/data_validator.py

All tests use a tmp_path fixture — no network calls.
"""

import pandas as pd
import pytest

from pipelines.publish.data_validator import DataValidator


# ── helpers ───────────────────────────────────────────────────────────────────


def _write_csv(path, df: pd.DataFrame, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, **kwargs)


@pytest.fixture
def validator(tmp_path):
    return DataValidator(curated_dir=tmp_path)


# ── check_bse_files_exist ─────────────────────────────────────────────────────


class TestCheckBSEFilesExist:
    def test_passes_when_core_file_present(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"scrip_code": "500325"}]),
        )
        result = validator.check_bse_files_exist()
        assert result.passed

    def test_fails_when_core_file_missing(self, validator, tmp_path):
        result = validator.check_bse_files_exist()
        assert not result.passed
        assert any("dim_bse_scrip_master.csv" in e for e in result.errors)

    def test_warns_when_optional_files_missing(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"scrip_code": "500325"}]),
        )
        result = validator.check_bse_files_exist()
        assert result.passed
        optional_warnings = [e for e in result.errors if "optional missing" in e]
        assert len(optional_warnings) > 0

    def test_fails_when_core_file_empty(self, validator, tmp_path):
        (tmp_path / "dim_bse_scrip_master.csv").touch()
        result = validator.check_bse_files_exist()
        assert not result.passed


# ── check_bse_scrip_codes_valid ───────────────────────────────────────────────


class TestCheckBSEScripCodesValid:
    def test_passes_for_six_digit_codes(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"scrip_code": "500325"}, {"scrip_code": "000001"}]),
        )
        result = validator.check_bse_scrip_codes_valid()
        assert result.passed

    def test_fails_for_non_six_digit_codes(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"scrip_code": "500325"}, {"scrip_code": "12345"}]),
        )
        result = validator.check_bse_scrip_codes_valid()
        assert not result.passed
        assert any("not exactly 6 digits" in e for e in result.errors)

    def test_fails_for_null_scrip_codes(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"scrip_code": "500325"}, {"scrip_code": None}]),
        )
        result = validator.check_bse_scrip_codes_valid()
        assert not result.passed
        assert any("null scrip_code" in e for e in result.errors)

    def test_skips_when_file_absent(self, validator, tmp_path):
        result = validator.check_bse_scrip_codes_valid()
        assert result.passed
        assert "skipping" in result.details


# ── check_bse_adjustment_factors_valid ───────────────────────────────────────


class TestCheckBSEAdjustmentFactorsValid:
    def test_passes_for_valid_factors(self, validator, tmp_path):
        _write_csv(
            tmp_path / "bse_fact_adjustment_factor.csv",
            pd.DataFrame(
                [
                    {
                        "scrip_id": 1,
                        "cumulative_split_adjustment": 0.5,
                        "cumulative_bonus_adjustment": 1.0,
                        "total_adjustment_factor": 0.5,
                    }
                ]
            ),
        )
        result = validator.check_bse_adjustment_factors_valid()
        assert result.passed

    def test_fails_for_non_positive_factor(self, validator, tmp_path):
        _write_csv(
            tmp_path / "bse_fact_adjustment_factor.csv",
            pd.DataFrame(
                [
                    {
                        "scrip_id": 1,
                        "cumulative_split_adjustment": -0.5,
                        "cumulative_bonus_adjustment": 1.0,
                        "total_adjustment_factor": -0.5,
                    }
                ]
            ),
        )
        result = validator.check_bse_adjustment_factors_valid()
        assert not result.passed

    def test_fails_for_extreme_factor(self, validator, tmp_path):
        _write_csv(
            tmp_path / "bse_fact_adjustment_factor.csv",
            pd.DataFrame(
                [
                    {
                        "scrip_id": 1,
                        "cumulative_split_adjustment": 1.0,
                        "cumulative_bonus_adjustment": 1.0,
                        "total_adjustment_factor": 9999,
                    }
                ]
            ),
        )
        result = validator.check_bse_adjustment_factors_valid()
        assert not result.passed

    def test_skips_when_file_absent(self, validator, tmp_path):
        result = validator.check_bse_adjustment_factors_valid()
        assert result.passed


# ── check_isin_bridge_integrity ───────────────────────────────────────────────


class TestCheckISINBridgeIntegrity:
    def test_passes_when_all_isins_resolve(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_security_master.csv",
            pd.DataFrame([{"isin": "INE001A01010", "security_id": 1}]),
        )
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"isin": "INE002A01010", "scrip_id": 1}]),
        )
        _write_csv(
            tmp_path / "fact_exchange_security_map.csv",
            pd.DataFrame(
                [
                    {"isin": "INE001A01010", "is_bse_only": False, "is_nse_only": True},
                    {"isin": "INE002A01010", "is_bse_only": True, "is_nse_only": False},
                ]
            ),
        )
        result = validator.check_isin_bridge_integrity()
        assert result.passed

    def test_fails_for_orphan_isin_in_bridge(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_security_master.csv",
            pd.DataFrame([{"isin": "INE001A01010", "security_id": 1}]),
        )
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"isin": "INE001A01010", "scrip_id": 1}]),
        )
        _write_csv(
            tmp_path / "fact_exchange_security_map.csv",
            pd.DataFrame(
                [
                    {
                        "isin": "INE001A01010",
                        "is_bse_only": False,
                        "is_nse_only": False,
                    },
                    {
                        "isin": "INE999A99999",
                        "is_bse_only": False,
                        "is_nse_only": False,
                    },
                ]
            ),
        )
        result = validator.check_isin_bridge_integrity()
        assert not result.passed
        assert any("not found in any security master" in e for e in result.errors)

    def test_skips_when_bridge_absent(self, validator, tmp_path):
        result = validator.check_isin_bridge_integrity()
        assert result.passed

    def test_reports_dual_listed_count(self, validator, tmp_path):
        _write_csv(
            tmp_path / "dim_security_master.csv",
            pd.DataFrame([{"isin": "INE001A01010", "security_id": 1}]),
        )
        _write_csv(
            tmp_path / "dim_bse_scrip_master.csv",
            pd.DataFrame([{"isin": "INE001A01010", "scrip_id": 1}]),
        )
        _write_csv(
            tmp_path / "fact_exchange_security_map.csv",
            pd.DataFrame(
                [{"isin": "INE001A01010", "is_bse_only": False, "is_nse_only": False}]
            ),
        )
        result = validator.check_isin_bridge_integrity()
        assert result.passed
        assert "dual-listed" in result.details


# ── run_bse_checks ────────────────────────────────────────────────────────────


class TestRunBSEChecks:
    def test_returns_list_of_check_results(self, validator, tmp_path):
        results = validator.run_bse_checks()
        assert isinstance(results, list)
        assert len(results) == 4  # 4 BSE checks

    def test_all_checks_skipped_gracefully_without_files(self, validator, tmp_path):
        results = validator.run_bse_checks()
        # bse_files_exist fails (core file missing); others skip (passed=True)
        names = {r.name for r in results}
        assert "bse_files_exist" in names
        assert "bse_scrip_codes_valid" in names
