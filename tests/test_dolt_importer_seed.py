"""
Tests for DoltImporter seed methods:
  - ensure_exchange_seeded()
  - ensure_action_types_seeded()

All tests are pure — no Dolt process, no file I/O.
_sql_json() and _run() are monkeypatched; seed file reads are patched via tmp_path.
"""

import subprocess
from unittest.mock import MagicMock

import pytest

from pipelines.publish.dolt_importer import DoltImporter


# ── fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture()
def imp():
    return DoltImporter.__new__(DoltImporter)  # skip __init__, no Dolt dir needed


# ── ensure_exchange_seeded ────────────────────────────────────────────────────


def test_exchange_already_present_does_not_insert(imp, monkeypatch):
    monkeypatch.setattr(imp, "_sql_json", lambda q: [{"exchange_id": 1}])
    inserted = []
    monkeypatch.setattr(imp, "_sql", lambda q: inserted.append(q))
    imp.ensure_exchange_seeded()
    assert inserted == [], "should not INSERT when exchange_id=1 exists"


def test_exchange_missing_inserts_nse_row(imp, monkeypatch):
    monkeypatch.setattr(imp, "_sql_json", lambda q: [])
    executed = []
    monkeypatch.setattr(imp, "_sql", lambda q: executed.append(q))
    imp.ensure_exchange_seeded()
    assert any("NSE" in q for q in executed), "should INSERT NSE row"


# ── ensure_action_types_seeded ────────────────────────────────────────────────


def test_action_types_already_seeded_skips_run(imp, monkeypatch):
    monkeypatch.setattr(imp, "_sql_json", lambda q: [{"n": 16}])
    run_calls = []
    monkeypatch.setattr(
        imp, "_run", lambda *a, **kw: run_calls.append(a) or MagicMock(returncode=0)
    )
    imp.ensure_action_types_seeded()
    assert run_calls == [], "should not call _run when table is already populated"


def test_action_types_empty_executes_seed_sql(imp, monkeypatch, tmp_path):
    monkeypatch.setattr(imp, "_sql_json", lambda q: [{"n": 0}])

    seed_content = (
        "INSERT IGNORE INTO dim_corporate_action_type (action_code) VALUES ('X');"
    )
    seed_file = tmp_path / "seed_corporate_actions.sql"
    seed_file.write_text(seed_content)
    monkeypatch.setattr("pipelines.publish.dolt_importer.DOLT_DIR", tmp_path)

    received = {}
    ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    monkeypatch.setattr(
        imp,
        "_run",
        lambda args, input_text=None: (
            received.update({"args": args, "sql": input_text}) or ok
        ),
    )

    imp.ensure_action_types_seeded()

    assert received.get("args") == ["sql"], "should call dolt sql"
    assert seed_content in (received.get("sql") or ""), "should pipe seed file content"


def test_action_types_seed_failure_raises(imp, monkeypatch, tmp_path):
    monkeypatch.setattr(imp, "_sql_json", lambda q: [{"n": 0}])

    seed_file = tmp_path / "seed_corporate_actions.sql"
    seed_file.write_text("bad sql;")
    monkeypatch.setattr("pipelines.publish.dolt_importer.DOLT_DIR", tmp_path)

    fail = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="syntax error"
    )
    monkeypatch.setattr(imp, "_run", lambda *a, **kw: fail)

    with pytest.raises(RuntimeError, match="Failed to seed dim_corporate_action_type"):
        imp.ensure_action_types_seeded()


def test_action_types_zero_count_row_treated_as_empty(imp, monkeypatch, tmp_path):
    """COUNT(*) returning n=0 should trigger seeding."""
    monkeypatch.setattr(imp, "_sql_json", lambda q: [{"n": 0}])

    seed_file = tmp_path / "seed_corporate_actions.sql"
    seed_file.write_text("-- seed")
    monkeypatch.setattr("pipelines.publish.dolt_importer.DOLT_DIR", tmp_path)

    ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    calls = []
    monkeypatch.setattr(imp, "_run", lambda *a, **kw: calls.append(a) or ok)

    imp.ensure_action_types_seeded()
    assert calls, "should call _run when count is 0"
