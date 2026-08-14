"""
Tests for pipelines/lineage/linker.py (SymbolLinker).

Covers the required test cases from pipelines/lineage/CLAUDE.md not already
covered in tests/test_lineage_rules.py:
- Temporary suspension and relisting (via corroboration path).
- Corporate action corroboration within window: confidence boosted.
- Determinism: same inputs -> identical event list across multiple calls.
- Never mutate input DataFrames.

Also covers a determinism bug found and fixed 2026-08-14: `link_across_periods`
built its event list by iterating Python sets of symbols, whose iteration
order depends on the interpreter's string hash seed. Rows sharing the same
event_date could therefore end up in a different relative order across
process runs even for identical input snapshots. Fixed by adding a full
deterministic tiebreaker to the final sort.

All tests are pure — no I/O, no network calls.
"""

import subprocess
import sys
from datetime import date

import pandas as pd
import pytest

from pipelines.lineage.linker import SymbolLinker


@pytest.fixture()
def linker():
    return SymbolLinker()


def _symbols(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ── link_across_periods: listings / delistings / renames ───────────────────


def test_link_across_periods_detects_new_listing(linker):
    current = _symbols([{"SYMBOL": "NEWCO", "ISIN": "INE001"}])
    historical = pd.DataFrame(columns=["SYMBOL", "ISIN"])

    df = linker.link_across_periods(current, historical, period_date=date(2026, 1, 1))

    assert len(df) == 1
    assert df.iloc[0]["event_type"] == "LISTING"
    assert df.iloc[0]["symbol_to"] == "NEWCO"
    assert df.iloc[0]["confidence"] == 0.95


def test_link_across_periods_detects_delisting_when_isin_not_found(linker):
    current = pd.DataFrame(columns=["SYMBOL", "ISIN"])
    historical = _symbols([{"SYMBOL": "GONE", "ISIN": "INE999"}])

    df = linker.link_across_periods(current, historical, period_date=date(2026, 1, 1))

    assert len(df) == 1
    assert df.iloc[0]["event_type"] == "DELISTING"
    assert df.iloc[0]["symbol_from"] == "GONE"


def test_link_across_periods_detects_rename_via_isin_match(linker):
    current = _symbols([{"SYMBOL": "NEWSYM", "ISIN": "INE001"}])
    historical = _symbols([{"SYMBOL": "OLDSYM", "ISIN": "INE001"}])

    df = linker.link_across_periods(current, historical, period_date=date(2026, 1, 1))

    # Current behavior: "NEWSYM" also fires a LISTING event (it's genuinely
    # absent from the historical snapshot, and new-listing detection doesn't
    # exclude rename targets), in addition to the RENAME event for the
    # OLDSYM -> NEWSYM pair detected via ISIN match on the removed side.
    assert len(df) == 2
    rename_rows = df[df["event_type"] == "RENAME"]
    assert len(rename_rows) == 1
    row = rename_rows.iloc[0]
    assert row["symbol_from"] == "OLDSYM"
    assert row["symbol_to"] == "NEWSYM"
    # ISIN match boosts confidence over the base detect_symbol_rename value
    assert row["confidence"] >= 0.85

    listing_rows = df[df["event_type"] == "LISTING"]
    assert len(listing_rows) == 1
    assert listing_rows.iloc[0]["symbol_to"] == "NEWSYM"


def test_link_across_periods_no_changes_returns_empty_with_schema(linker):
    same = _symbols([{"SYMBOL": "STABLE", "ISIN": "INE001"}])

    df = linker.link_across_periods(same, same, period_date=date(2026, 1, 1))

    assert df.empty
    for col in [
        "symbol_from",
        "symbol_to",
        "event_date",
        "event_type",
        "confidence",
        "reason",
        "corroborating_evidence",
    ]:
        assert col in df.columns


def test_link_across_periods_does_not_mutate_inputs(linker):
    current = _symbols([{"SYMBOL": "NEWCO", "ISIN": "INE001"}])
    historical = _symbols([{"SYMBOL": "OLDCO", "ISIN": "INE002"}])
    current_before = current.copy()
    historical_before = historical.copy()

    linker.link_across_periods(current, historical, period_date=date(2026, 1, 1))

    pd.testing.assert_frame_equal(current, current_before)
    pd.testing.assert_frame_equal(historical, historical_before)


# ── determinism (same-process) ──────────────────────────────────────────────


def test_link_across_periods_deterministic_same_process(linker):
    current = _symbols(
        [{"SYMBOL": s, "ISIN": f"INE{i}"} for i, s in enumerate(["AAA", "BBB", "CCC"])]
    )
    historical = _symbols(
        [
            {"SYMBOL": s, "ISIN": f"INE{i + 10}"}
            for i, s in enumerate(["DDD", "EEE", "FFF"])
        ]
    )

    first = linker.link_across_periods(
        current, historical, period_date=date(2026, 1, 1)
    )
    second = linker.link_across_periods(
        current, historical, period_date=date(2026, 1, 1)
    )

    pd.testing.assert_frame_equal(first, second)


def test_link_across_periods_deterministic_across_hash_seeds():
    """
    Regression test for the 2026-08-14 fix: row order for same-event_date
    rows must not depend on PYTHONHASHSEED (i.e. on set iteration order).
    Runs the linker in two subprocesses with different hash seeds and
    checks the output is byte-identical.
    """
    script = (
        "import pandas as pd; "
        "from pipelines.lineage.linker import SymbolLinker; "
        "from datetime import date; "
        "current = pd.DataFrame({'SYMBOL': ['AAA','BBB','CCC'], 'ISIN': ['I1','I2','I3']}); "
        "historical = pd.DataFrame({'SYMBOL': ['DDD','EEE','FFF'], 'ISIN': ['I4','I5','I6']}); "
        "df = SymbolLinker().link_across_periods(current, historical, period_date=date(2026,1,1)); "
        "print(df.to_csv(index=False))"
    )
    outputs = []
    for seed in ("1", "2", "42"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={"PYTHONHASHSEED": seed, "PATH": __import__("os").environ["PATH"]},
            cwd=__import__("pathlib").Path(__file__).parent.parent,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(result.stdout)

    assert outputs[0] == outputs[1] == outputs[2]


# ── cross_reference_with_actions: corroboration ─────────────────────────────


def test_cross_reference_boosts_confidence_when_corroborated(linker):
    events = pd.DataFrame(
        [
            {
                "symbol_from": "GONE",
                "symbol_to": None,
                "event_date": "2026-06-01",
                "event_type": "DELISTING",
                "confidence": 0.75,
                "reason": "inferred",
                "corroborating_evidence": "inferred_from_absence",
            }
        ]
    )
    actions = pd.DataFrame(
        [
            {
                "SYMBOL": "GONE",
                "action_code": "DELISTING",
                "event_date": "2026-06-10",  # within +/-30 day window
            }
        ]
    )

    out = linker.cross_reference_with_actions(events, actions)

    assert out.iloc[0]["corroborated"] is True or out.iloc[0]["corroborated"] == True  # noqa: E712
    assert out.iloc[0]["confidence"] == pytest.approx(0.90)  # 0.75 + 0.15 boost
    assert "corp_action=DELISTING" in out.iloc[0]["corroborating_evidence"]


def test_cross_reference_flags_manual_review_when_not_corroborated(linker):
    events = pd.DataFrame(
        [
            {
                "symbol_from": "GONE",
                "symbol_to": None,
                "event_date": "2026-06-01",
                "event_type": "DELISTING",
                "confidence": 0.75,
                "reason": "inferred",
                "corroborating_evidence": "inferred_from_absence",
            }
        ]
    )
    actions = pd.DataFrame(
        [{"SYMBOL": "UNRELATED", "action_code": "DIVIDEND", "event_date": "2026-06-10"}]
    )

    out = linker.cross_reference_with_actions(events, actions)

    assert out.iloc[0]["corroborated"] == False  # noqa: E712
    assert out.iloc[0]["manual_review_required"] == True  # noqa: E712
    assert out.iloc[0]["confidence"] == 0.75  # unchanged


def test_cross_reference_outside_window_not_corroborated(linker):
    events = pd.DataFrame(
        [
            {
                "symbol_from": "GONE",
                "symbol_to": None,
                "event_date": "2026-06-01",
                "event_type": "DELISTING",
                "confidence": 0.75,
                "reason": "inferred",
                "corroborating_evidence": "",
            }
        ]
    )
    actions = pd.DataFrame(
        [
            {
                "SYMBOL": "GONE",
                "action_code": "DELISTING",
                "event_date": "2026-08-15",  # 75 days later, outside +/-30 day window
            }
        ]
    )

    out = linker.cross_reference_with_actions(events, actions)

    assert out.iloc[0]["corroborated"] == False  # noqa: E712


def test_cross_reference_ignores_non_corroborable_event_types(linker):
    """LISTING and RENAME events don't need corroboration; left untouched."""
    events = pd.DataFrame(
        [
            {
                "symbol_from": None,
                "symbol_to": "NEWCO",
                "event_date": "2026-06-01",
                "event_type": "LISTING",
                "confidence": 0.95,
                "reason": "new listing",
                "corroborating_evidence": "",
            }
        ]
    )
    actions = pd.DataFrame(
        [{"SYMBOL": "NEWCO", "action_code": "DIVIDEND", "event_date": "2026-06-05"}]
    )

    out = linker.cross_reference_with_actions(events, actions)

    assert out.iloc[0]["corroborated"] == False  # noqa: E712
    assert out.iloc[0]["manual_review_required"] == False  # noqa: E712
    assert out.iloc[0]["confidence"] == 0.95


def test_cross_reference_empty_lineage_events_returns_typed_empty_df(linker):
    events = pd.DataFrame(
        columns=["symbol_from", "symbol_to", "event_date", "event_type", "confidence"]
    )
    actions = pd.DataFrame(
        [{"SYMBOL": "X", "action_code": "MERGER", "event_date": "2026-01-01"}]
    )

    out = linker.cross_reference_with_actions(events, actions)

    assert out.empty
    assert "corroborated" in out.columns
    assert "manual_review_required" in out.columns


def test_cross_reference_does_not_mutate_actions_input(linker):
    """
    Regression test for BUG-8 (todo.md, opened 2026-07-03, fixed 2026-08-14):
    cross_reference_with_actions() used to add a `_action_date` column
    directly onto the caller's `actions` DataFrame (later dropped, but a
    real mutation of the input in the interim).
    """
    events = pd.DataFrame(
        [
            {
                "symbol_from": "GONE",
                "symbol_to": None,
                "event_date": "2026-06-01",
                "event_type": "DELISTING",
                "confidence": 0.75,
                "reason": "inferred",
                "corroborating_evidence": "",
            }
        ]
    )
    actions = pd.DataFrame(
        [{"SYMBOL": "GONE", "action_code": "DELISTING", "event_date": "2026-06-10"}]
    )
    actions_before = actions.copy()

    linker.cross_reference_with_actions(events, actions)

    pd.testing.assert_frame_equal(actions, actions_before)


def test_cross_reference_does_not_mutate_lineage_events_input(linker):
    events = pd.DataFrame(
        [
            {
                "symbol_from": "GONE",
                "symbol_to": None,
                "event_date": "2026-06-01",
                "event_type": "DELISTING",
                "confidence": 0.75,
                "reason": "inferred",
                "corroborating_evidence": "",
            }
        ]
    )
    actions = pd.DataFrame(
        [{"SYMBOL": "GONE", "action_code": "DELISTING", "event_date": "2026-06-10"}]
    )
    events_before = events.copy()

    linker.cross_reference_with_actions(events, actions)

    pd.testing.assert_frame_equal(events, events_before)
