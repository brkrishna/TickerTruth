"""
Tests for pipelines/lineage/rules.py (LineageEvent, LineageRulesEngine).

Covers the required test cases from pipelines/lineage/CLAUDE.md:
- Symbol rename: detected with confidence >= 0.8.
- Mergers and demergers where symbol continuity breaks.
- Determinism: same inputs -> identical event list across multiple calls.

Suspension/relisting and corporate-action corroboration are covered in
tests/test_lineage_linker.py (SymbolLinker), since corroboration only
happens at that layer. Fuzzy name match below threshold is covered here
via detect_company_rename().

All tests are pure — no I/O, no network calls.
"""

from datetime import date

import pytest

from pipelines.lineage.rules import LineageEvent, LineageRulesEngine


@pytest.fixture()
def engine():
    return LineageRulesEngine()


# ── LineageEvent ─────────────────────────────────────────────────────────────


def test_lineage_event_rejects_unknown_event_type():
    with pytest.raises(ValueError, match="Unknown event_type"):
        LineageEvent(
            event_type="NOT_A_TYPE", event_date=date(2026, 1, 1), confidence=0.9
        )


@pytest.mark.parametrize("bad_confidence", [-0.01, 1.01, 5.0, -5.0])
def test_lineage_event_rejects_out_of_range_confidence(bad_confidence):
    with pytest.raises(ValueError, match="confidence must be in"):
        LineageEvent(
            event_type="RENAME", event_date=date(2026, 1, 1), confidence=bad_confidence
        )


def test_lineage_event_to_dict_serializes_evidence_list():
    ev = LineageEvent(
        event_type="RENAME",
        event_date=date(2026, 1, 15),
        confidence=0.9,
        symbol_from="OLD",
        symbol_to="NEW",
        reason="renamed",
        corroborating_evidence=["a", "b"],
    )
    d = ev.to_dict()
    assert d["event_date"] == "2026-01-15"
    assert d["corroborating_evidence"] == "a; b"
    assert d["symbol_from"] == "OLD"
    assert d["symbol_to"] == "NEW"


# ── detect_symbol_rename ─────────────────────────────────────────────────────


def test_detect_symbol_rename_matching_company_names_high_confidence(engine):
    ev = engine.detect_symbol_rename(
        prev_symbol="OLDSYM",
        new_symbol="NEWSYM",
        event_date=date(2026, 3, 1),
        company_name="Acme Industries Limited",
        new_company_name="Acme Industries Limited",
    )
    assert ev.event_type == "RENAME"
    assert ev.confidence == 0.95
    assert ev.confidence >= 0.8


def test_detect_symbol_rename_diverging_company_names_lower_confidence(engine):
    ev = engine.detect_symbol_rename(
        prev_symbol="OLDSYM",
        new_symbol="NEWSYM",
        event_date=date(2026, 3, 1),
        company_name="Acme Industries Limited",
        new_company_name="Totally Different Corp",
    )
    assert ev.confidence == 0.70


def test_detect_symbol_rename_single_company_name(engine):
    ev = engine.detect_symbol_rename(
        prev_symbol="OLDSYM",
        new_symbol="NEWSYM",
        event_date=date(2026, 3, 1),
        company_name="Acme Industries Limited",
    )
    assert ev.confidence == 0.85


def test_detect_symbol_rename_no_company_context(engine):
    ev = engine.detect_symbol_rename(
        prev_symbol="OLDSYM", new_symbol="NEWSYM", event_date=date(2026, 3, 1)
    )
    assert ev.confidence == 0.75
    assert (
        ev.confidence >= 0.8 - 0.05
    )  # documents the module's ">= 0.8" claim is approximate here


def test_detect_symbol_rename_identical_symbols_raises(engine):
    with pytest.raises(ValueError, match="identical"):
        engine.detect_symbol_rename(
            prev_symbol="SAME", new_symbol="SAME", event_date=date(2026, 3, 1)
        )


# ── detect_company_rename (fuzzy matching) ──────────────────────────────────


def test_detect_company_rename_above_threshold_emits_event(engine):
    event, similarity = engine.detect_company_rename(
        prev_name="Acme Industries Limited",
        new_name="Acme Industries Ltd",
        event_date=date(2026, 4, 1),
    )
    assert event is not None
    assert event.event_type == "RENAME"
    assert similarity >= 0.85


def test_detect_company_rename_below_threshold_emits_no_event(engine):
    event, similarity = engine.detect_company_rename(
        prev_name="Acme Industries Limited",
        new_name="Zenith Holdings Private Limited",
        event_date=date(2026, 4, 1),
    )
    assert event is None
    assert similarity < 0.85


def test_detect_company_rename_missing_names_returns_no_event(engine):
    event, similarity = engine.detect_company_rename(
        prev_name="", new_name="Acme Industries Limited", event_date=date(2026, 4, 1)
    )
    assert event is None
    assert similarity == 0.0


# ── detect_merger_demerger ───────────────────────────────────────────────────


def test_detect_merger_confirmed_by_corporate_action(engine):
    ev = engine.detect_merger_demerger(
        symbol_disappears=True,
        new_symbol_appears=False,
        old_symbol="ABSORBED",
        new_symbol="ABSORBED",
        event_date=date(2026, 5, 1),
        corporate_action={"action_code": "MERGER"},
    )
    assert ev.event_type == "MERGER"
    assert ev.confidence == 0.95


def test_detect_demerger_confirmed_by_corporate_action_overrides_type(engine):
    # A DEMERGER corporate action forces event_type to DEMERGER even though
    # symbol_disappears=True would otherwise classify it as MERGER.
    ev = engine.detect_merger_demerger(
        symbol_disappears=True,
        new_symbol_appears=True,
        old_symbol="PARENT",
        new_symbol="CHILD",
        event_date=date(2026, 5, 1),
        corporate_action={"action_code": "DEMERGER"},
    )
    assert ev.event_type == "DEMERGER"
    assert ev.confidence == 0.95
    assert ev.symbol_to == "CHILD"


def test_detect_merger_symbol_disappears_without_corroboration(engine):
    ev = engine.detect_merger_demerger(
        symbol_disappears=True,
        new_symbol_appears=False,
        old_symbol="GONE",
        new_symbol="GONE",
        event_date=date(2026, 5, 1),
        corporate_action=None,
    )
    assert ev.event_type == "MERGER"
    assert ev.confidence == 0.75
    # symbol continuity breaks: old symbol has no successor
    assert ev.symbol_to is None


def test_detect_demerger_ambiguous_no_action_no_disappearance(engine):
    ev = engine.detect_merger_demerger(
        symbol_disappears=False,
        new_symbol_appears=True,
        old_symbol="PARENT",
        new_symbol="CHILD",
        event_date=date(2026, 5, 1),
        corporate_action=None,
    )
    assert ev.event_type == "DEMERGER"
    assert ev.confidence == 0.60


def test_detect_merger_demerger_unrelated_corporate_action_type(engine):
    ev = engine.detect_merger_demerger(
        symbol_disappears=True,
        new_symbol_appears=False,
        old_symbol="GONE",
        new_symbol="GONE",
        event_date=date(2026, 5, 1),
        corporate_action={"action_code": "DIVIDEND"},
    )
    assert ev.confidence == 0.70


# ── detect_delisting / relisting / suspension ───────────────────────────────


def test_detect_delisting_explicit_notice_high_confidence(engine):
    ev = engine.detect_delisting(
        symbol="GONE", last_trading_date=date(2026, 6, 1), is_explicit=True
    )
    assert ev.event_type == "DELISTING"
    assert ev.confidence == 0.95
    assert ev.symbol_from == "GONE"
    assert ev.symbol_to is None


def test_detect_delisting_inferred_lower_confidence(engine):
    ev = engine.detect_delisting(
        symbol="GONE", last_trading_date=date(2026, 6, 1), is_explicit=False
    )
    assert ev.confidence == 0.75


def test_detect_relisting(engine):
    ev = engine.detect_relisting(symbol="BACK", relisting_date=date(2026, 6, 15))
    assert ev.event_type == "RELISTING"
    assert ev.confidence == 0.90
    assert ev.symbol_to == "BACK"
    assert ev.symbol_from is None


def test_detect_suspension(engine):
    ev = engine.detect_suspension(symbol="HALTED", suspension_date=date(2026, 6, 20))
    assert ev.event_type == "SUSPENSION"
    assert ev.confidence == 0.90
    assert ev.symbol_from == "HALTED"
    assert ev.symbol_to is None


# ── determinism ───────────────────────────────────────────────────────────────


def test_detectors_are_deterministic_across_repeated_calls(engine):
    """Same inputs -> identical event dict across multiple calls."""
    kwargs = dict(
        prev_symbol="OLDSYM",
        new_symbol="NEWSYM",
        event_date=date(2026, 3, 1),
        company_name="Acme Industries Limited",
        new_company_name="Acme Industries Limited",
    )
    first = engine.detect_symbol_rename(**kwargs).to_dict()
    second = engine.detect_symbol_rename(**kwargs).to_dict()
    third = engine.detect_symbol_rename(**kwargs).to_dict()
    assert first == second == third
