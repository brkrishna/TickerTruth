"""
Tests for the validate-gate on the Dolt commit in run_load() (BUG-7).

Verifies that:
- import_all() always runs regardless of validate_passed
- commit() is skipped when validate_passed=False
- commit() runs when validate_passed=True
- validate result is threaded correctly from main() into run_load()
"""

from datetime import date
from unittest.mock import MagicMock, patch

from pipelines.run import run_load, main


RUN_DATE = date(2026, 6, 1)


def _mock_importer(commit_hash="abc123"):
    """Return a DoltImporter mock with a successful import_all and commit."""
    importer = MagicMock()
    importer.import_all.return_value = {
        "tables": {"dim_security_master": {"status": "ok", "rows": 10}},
        "errors": [],
    }
    importer.commit.return_value = commit_hash
    return importer


# ── run_load validate gate ────────────────────────────────────────────────────


def test_commit_skipped_when_validate_failed(monkeypatch):
    """Dolt commit must not be called when validate_passed=False."""
    importer = _mock_importer()
    with patch("pipelines.publish.dolt_importer.DoltImporter", return_value=importer):
        ok = run_load(
            RUN_DATE, dry_run=False, no_dolt_commit=False, validate_passed=False
        )

    assert ok is True, (
        "load should still report success — import ran, commit intentionally skipped"
    )
    importer.import_all.assert_called_once()
    importer.commit.assert_not_called()


def test_commit_runs_when_validate_passed(monkeypatch):
    """Dolt commit must be called when validate_passed=True."""
    importer = _mock_importer()
    with patch("pipelines.publish.dolt_importer.DoltImporter", return_value=importer):
        ok = run_load(
            RUN_DATE, dry_run=False, no_dolt_commit=False, validate_passed=True
        )

    assert ok is True
    importer.commit.assert_called_once()


def test_commit_skipped_by_dry_run_regardless_of_validate(monkeypatch):
    """dry_run always suppresses the commit, independent of validate_passed."""
    importer = _mock_importer()
    with patch("pipelines.publish.dolt_importer.DoltImporter", return_value=importer):
        ok = run_load(
            RUN_DATE, dry_run=True, no_dolt_commit=False, validate_passed=True
        )

    assert ok is True
    importer.commit.assert_not_called()


def test_commit_skipped_by_no_dolt_commit_flag(monkeypatch):
    """--no-dolt-commit suppresses the commit when validate passed."""
    importer = _mock_importer()
    with patch("pipelines.publish.dolt_importer.DoltImporter", return_value=importer):
        ok = run_load(
            RUN_DATE, dry_run=False, no_dolt_commit=True, validate_passed=True
        )

    assert ok is True
    importer.commit.assert_not_called()


def test_validate_default_true_allows_commit(monkeypatch):
    """When validate_passed is not supplied it defaults to True — commit proceeds."""
    importer = _mock_importer()
    with patch("pipelines.publish.dolt_importer.DoltImporter", return_value=importer):
        ok = run_load(RUN_DATE, dry_run=False, no_dolt_commit=False)

    assert ok is True
    importer.commit.assert_called_once()


def test_import_all_error_returns_false_regardless_of_validate(monkeypatch):
    """If import_all itself fails, load returns False even with validate passing."""
    importer = _mock_importer()
    importer.import_all.return_value = {
        "tables": {},
        "errors": ["fact_symbol_lineage_event: column mismatch"],
    }
    with patch("pipelines.publish.dolt_importer.DoltImporter", return_value=importer):
        ok = run_load(
            RUN_DATE, dry_run=False, no_dolt_commit=False, validate_passed=True
        )

    assert ok is False
    importer.commit.assert_not_called()


# ── main() integration ────────────────────────────────────────────────────────


def _stub_task(result):
    """Return a no-arg callable that returns result."""
    return lambda *a, **kw: result


def test_main_passes_validate_failure_to_load(monkeypatch):
    """When validate fails in main(), run_load receives validate_passed=False."""
    captured = {}

    def fake_run_load(run_date, dry_run, no_dolt_commit, validate_passed=True, stats=None):
        captured["validate_passed"] = validate_passed
        return True

    monkeypatch.setattr("pipelines.run.run_extract", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_normalize", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_lineage", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_adjust", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_validate", _stub_task(False))  # FAIL
    monkeypatch.setattr("pipelines.run.run_load", fake_run_load)
    monkeypatch.setattr("pipelines.run.run_export", _stub_task({}))
    monkeypatch.setattr("pipelines.run.run_manifest", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_release_notes", _stub_task(True))

    main(["--date", "2026-06-01"])

    assert captured["validate_passed"] is False


def test_main_passes_validate_success_to_load(monkeypatch):
    """When validate passes in main(), run_load receives validate_passed=True."""
    captured = {}

    def fake_run_load(run_date, dry_run, no_dolt_commit, validate_passed=True, stats=None):
        captured["validate_passed"] = validate_passed
        return True

    monkeypatch.setattr("pipelines.run.run_extract", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_normalize", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_lineage", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_adjust", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_validate", _stub_task(True))  # PASS
    monkeypatch.setattr("pipelines.run.run_load", fake_run_load)
    monkeypatch.setattr("pipelines.run.run_export", _stub_task({}))
    monkeypatch.setattr("pipelines.run.run_manifest", _stub_task(True))
    monkeypatch.setattr("pipelines.run.run_release_notes", _stub_task(True))

    main(["--date", "2026-06-01"])

    assert captured["validate_passed"] is True


def test_main_load_without_validate_in_tasks_defaults_to_true(monkeypatch):
    """Running --tasks load without validate defaults validate_passed to True."""
    captured = {}

    def fake_run_load(run_date, dry_run, no_dolt_commit, validate_passed=True, stats=None):
        captured["validate_passed"] = validate_passed
        return True

    monkeypatch.setattr("pipelines.run.run_load", fake_run_load)

    main(["--date", "2026-06-01", "--tasks", "load"])

    assert captured["validate_passed"] is True
