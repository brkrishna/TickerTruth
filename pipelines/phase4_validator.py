"""
Phase 4 unit tests — CI/CD, orchestrator, runbook.

Run:
    pytest pipelines/phase4_validator.py -v
"""

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent


def _get_triggers(content: dict) -> dict:
    """
    PyYAML parses the GitHub Actions `on:` key as boolean True
    (because `on` is a YAML alias for `true`).
    This helper normalises the lookup to handle both.
    """
    return content.get(True, content.get("on", {}))


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 1 — GitHub Actions Workflows
# ═══════════════════════════════════════════════════════════════════════════════

WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"
WORKFLOWS = ["ci.yml", "nightly.yml", "release.yml"]


class TestWorkflowFilesExist:
    def test_ci_workflow_exists(self):
        assert (WORKFLOW_DIR / "ci.yml").exists()

    def test_nightly_workflow_exists(self):
        assert (WORKFLOW_DIR / "nightly.yml").exists()

    def test_release_workflow_exists(self):
        assert (WORKFLOW_DIR / "release.yml").exists()


class TestWorkflowYAMLValid:
    @pytest.mark.parametrize("filename", WORKFLOWS)
    def test_parses_as_valid_yaml(self, filename):
        path = WORKFLOW_DIR / filename
        content = yaml.safe_load(path.read_text())
        assert isinstance(content, dict), f"{filename} did not parse to a dict"

    @pytest.mark.parametrize("filename", WORKFLOWS)
    def test_has_name_field(self, filename):
        content = yaml.safe_load((WORKFLOW_DIR / filename).read_text())
        assert "name" in content, f"{filename} missing 'name'"

    @pytest.mark.parametrize("filename", WORKFLOWS)
    def test_has_on_trigger(self, filename):
        content = yaml.safe_load((WORKFLOW_DIR / filename).read_text())
        # PyYAML parses the YAML `on:` key as the boolean True (YAML alias for true)
        has_on = "on" in content or True in content
        assert has_on, f"{filename} missing 'on' trigger"

    @pytest.mark.parametrize("filename", WORKFLOWS)
    def test_has_jobs(self, filename):
        content = yaml.safe_load((WORKFLOW_DIR / filename).read_text())
        assert "jobs" in content and content["jobs"], f"{filename} has no jobs"


class TestCIWorkflowContent:
    def _content(self):
        return yaml.safe_load((WORKFLOW_DIR / "ci.yml").read_text())

    def test_triggers_on_push_to_main(self):
        content = self._content()
        triggers = _get_triggers(content)
        assert "push" in triggers
        branches = triggers["push"].get("branches", [])
        assert "main" in branches

    def test_triggers_on_pull_request(self):
        content = self._content()
        triggers = _get_triggers(content)
        assert "pull_request" in triggers

    def test_has_lint_job(self):
        content = self._content()
        job_names = list(content["jobs"].keys())
        assert any("lint" in j.lower() for j in job_names)

    def test_has_test_job(self):
        content = self._content()
        job_names = list(content["jobs"].keys())
        assert any("test" in j.lower() for j in job_names)

    def test_lint_runs_black(self):
        content = self._content()
        lint_job = content["jobs"].get("lint", {})
        steps = lint_job.get("steps", [])
        all_cmds = " ".join(str(s.get("run", "")) for s in steps)
        assert "black" in all_cmds

    def test_test_job_runs_pytest(self):
        content = self._content()
        test_job = content["jobs"].get("test", {})
        steps = test_job.get("steps", [])
        all_cmds = " ".join(str(s.get("run", "")) for s in steps)
        assert "pytest" in all_cmds


class TestNightlyWorkflowContent:
    def _content(self):
        return yaml.safe_load((WORKFLOW_DIR / "nightly.yml").read_text())

    def test_has_cron_schedule(self):
        content = self._content()
        triggers = _get_triggers(content)
        schedules = triggers.get("schedule", [])
        assert schedules, "nightly.yml has no cron schedule"
        crons = [s["cron"] for s in schedules]
        assert any(crons), "No cron expression found"

    def test_has_workflow_dispatch(self):
        content = self._content()
        triggers = _get_triggers(content)
        assert "workflow_dispatch" in triggers

    def test_workflow_dispatch_has_dry_run_input(self):
        content = self._content()
        inputs = _get_triggers(content).get("workflow_dispatch", {}).get("inputs", {})
        assert "dry_run" in inputs

    def test_pipeline_run_step_calls_run_py(self):
        content = self._content()
        job = list(content["jobs"].values())[0]
        all_cmds = " ".join(str(s.get("run", "")) for s in job.get("steps", []))
        assert "run.py" in all_cmds


class TestReleaseWorkflowContent:
    def _content(self):
        return yaml.safe_load((WORKFLOW_DIR / "release.yml").read_text())

    def test_triggers_on_version_tags(self):
        content = self._content()
        triggers = _get_triggers(content)
        assert "push" in triggers
        tags = triggers["push"].get("tags", [])
        assert any("v*" in t or t.startswith("v") for t in tags)

    def test_creates_github_release(self):
        content = self._content()
        all_uses = " ".join(
            str(s.get("uses", ""))
            for job in content["jobs"].values()
            for s in job.get("steps", [])
        )
        assert "action-gh-release" in all_uses or "release" in all_uses.lower()


class TestPytestIni:
    def test_pytest_ini_exists(self):
        assert (PROJECT_ROOT / "pytest.ini").exists()

    def test_pytest_ini_has_testpaths(self):
        ini = (PROJECT_ROOT / "pytest.ini").read_text()
        assert "testpaths" in ini

    def test_pytest_ini_includes_pipelines(self):
        ini = (PROJECT_ROOT / "pytest.ini").read_text()
        assert "pipelines" in ini


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 2 — Pipeline Orchestrator (run.py)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRunPyImport:
    def test_run_py_exists(self):
        assert (PROJECT_ROOT / "pipelines" / "run.py").exists()

    def test_imports_cleanly(self):
        from pipelines.run import main, parse_args, ALL_TASKS

        assert callable(main)
        assert callable(parse_args)
        assert len(ALL_TASKS) > 0

    def test_all_tasks_list(self):
        from pipelines.run import ALL_TASKS

        required = {
            "extract",
            "normalize",
            "lineage",
            "adjust",
            "validate",
            "load",
            "export",
            "manifest",
            "release-notes",
        }
        assert required <= set(ALL_TASKS)


class TestRunPyArgParser:
    def test_default_args_no_error(self):
        from pipelines.run import parse_args

        args = parse_args([])
        assert args.dry_run is False
        assert args.no_fetch is False
        assert args.date is None

    def test_date_argument(self):
        from pipelines.run import parse_args

        args = parse_args(["--date", "2024-06-01"])
        assert args.date == "2024-06-01"

    def test_dry_run_flag(self):
        from pipelines.run import parse_args

        args = parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_no_fetch_flag(self):
        from pipelines.run import parse_args

        args = parse_args(["--no-fetch"])
        assert args.no_fetch is True

    def test_no_dolt_commit_flag(self):
        from pipelines.run import parse_args

        args = parse_args(["--no-dolt-commit"])
        assert args.no_dolt_commit is True

    def test_tasks_argument(self):
        from pipelines.run import parse_args

        args = parse_args(["--tasks", "validate,export"])
        assert "validate" in args.tasks
        assert "export" in args.tasks

    def test_resolve_date_today(self):
        from pipelines.run import resolve_date
        from datetime import date

        d = resolve_date(None)
        assert isinstance(d, date)

    def test_resolve_date_specific(self):
        from pipelines.run import resolve_date
        from datetime import date

        d = resolve_date("2024-06-01")
        assert d == date(2024, 6, 1)

    def test_resolve_date_bad_format_exits(self):
        from pipelines.run import resolve_date

        with pytest.raises(SystemExit) as exc:
            resolve_date("01/06/2024")
        assert exc.value.code == 2

    def test_unknown_task_returns_exit_2(self):
        from pipelines.run import main

        code = main(["--tasks", "nonexistent_task"])
        assert code == 2


class TestRunPyTaskRunners:
    """Unit-test individual task runner functions with mocks."""

    def test_run_validate_passes_with_good_curated(self, tmp_path):
        """run_validate should return True when all curated checks pass."""
        from pipelines.run import run_validate
        from datetime import date
        from pipelines.publish.data_validator import DataValidator
        from unittest.mock import patch, MagicMock

        good_result = MagicMock()
        good_result.passed = True
        good_result.name = "test_check"
        good_result.details = "ok"
        good_result.errors = []

        with patch.object(
            DataValidator, "run_curated_checks", return_value=[good_result]
        ):
            ok = run_validate(date.today())
        assert ok is True

    def test_run_validate_fails_with_bad_curated(self):
        from pipelines.run import run_validate
        from datetime import date
        from pipelines.publish.data_validator import DataValidator
        from unittest.mock import patch, MagicMock

        bad_result = MagicMock()
        bad_result.passed = False
        bad_result.name = "bad_check"
        bad_result.details = "failed"
        bad_result.errors = ["something wrong"]

        with patch.object(
            DataValidator, "run_curated_checks", return_value=[bad_result]
        ):
            ok = run_validate(date.today())
        assert ok is False


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT 3 — Runbook
# ═══════════════════════════════════════════════════════════════════════════════

RUNBOOK_PATH = PROJECT_ROOT / "docs" / "runbook.md"

REQUIRED_SECTIONS = [
    "Prerequisites",
    "Manual Refresh Procedure",
    "Troubleshooting",
    "Monitoring",
    "Failure Recovery",
    "Release Checklist",
]

REQUIRED_COMMANDS = [
    "pipelines/run.py",
    "dolt",
    "playwright",
    "pytest",
]


class TestRunbook:
    def test_runbook_exists(self):
        assert RUNBOOK_PATH.exists(), "docs/runbook.md not found"

    def test_runbook_not_empty(self):
        assert RUNBOOK_PATH.stat().st_size > 500

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_runbook_has_section(self, section):
        content = RUNBOOK_PATH.read_text()
        assert section in content, f"Runbook missing section: {section}"

    @pytest.mark.parametrize("cmd", REQUIRED_COMMANDS)
    def test_runbook_mentions_command(self, cmd):
        content = RUNBOOK_PATH.read_text()
        assert cmd in content, f"Runbook does not mention command: {cmd}"

    def test_runbook_has_code_blocks(self):
        content = RUNBOOK_PATH.read_text()
        assert "```" in content, "Runbook has no code blocks (fenced ```)"

    def test_runbook_mentions_rollback(self):
        content = RUNBOOK_PATH.read_text().lower()
        assert "rollback" in content

    def test_runbook_mentions_dry_run(self):
        content = RUNBOOK_PATH.read_text()
        assert "--dry-run" in content
