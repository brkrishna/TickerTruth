"""
Tests for DoltImporter.transform_lineage_events().

All tests are pure — no Dolt process, no file I/O.
The transform method is called directly; _get_symbol_id_map() is monkeypatched
to return a controlled symbol → security_id mapping.
"""

import pandas as pd
import pytest

from pipelines.publish.dolt_importer import DoltImporter, _LINEAGE_EVENT_TYPE_MAP


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def importer(monkeypatch):
    """DoltImporter with _get_symbol_id_map patched to a static lookup."""
    imp = DoltImporter.__new__(DoltImporter)  # skip __init__ (no Dolt dir needed)
    monkeypatch.setattr(
        imp,
        "_get_symbol_id_map",
        lambda: {"INFY": 1, "TCS": 2, "WIPRO": 3, "OLDNAME": 4},
    )
    return imp


def _lineage_row(
    symbol_from=None,
    symbol_to=None,
    event_date="2026-01-15",
    event_type="RENAME",
    confidence=0.85,
    reason="test",
    corroborating_evidence="",
) -> dict:
    return {
        "symbol_from": symbol_from,
        "symbol_to": symbol_to,
        "event_date": event_date,
        "event_type": event_type,
        "confidence": confidence,
        "reason": reason,
        "corroborating_evidence": corroborating_evidence,
    }


# ── happy-path tests ──────────────────────────────────────────────────────────


def test_rename_event_columns_mapped(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="OLDNAME", symbol_to="INFY", event_type="RENAME")]
    )
    out = importer.transform_lineage_events(df)

    assert "old_symbol" in out.columns
    assert "new_symbol" in out.columns
    assert "change_date" in out.columns
    assert "change_reason" in out.columns
    assert "security_id" in out.columns
    assert "source" in out.columns


def test_rename_values_correct(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="OLDNAME", symbol_to="INFY", event_type="RENAME")]
    )
    out = importer.transform_lineage_events(df)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["old_symbol"] == "OLDNAME"
    assert row["new_symbol"] == "INFY"
    assert row["change_date"] == "2026-01-15"
    assert row["change_reason"] == "rename"
    assert row["security_id"] == 4  # OLDNAME resolves first
    assert row["source"] == "lineage_pipeline"


def test_merger_populates_merged_with_symbol(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="TCS", symbol_to="INFY", event_type="MERGER")]
    )
    out = importer.transform_lineage_events(df)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["change_reason"] == "merger"
    assert row["merged_with_symbol"] == "INFY"


def test_non_merger_merged_with_symbol_is_none(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="OLDNAME", symbol_to="INFY", event_type="RENAME")]
    )
    out = importer.transform_lineage_events(df)
    assert out.iloc[0]["merged_with_symbol"] is None


def test_demerger_maps_to_merger_enum(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="TCS", symbol_to="WIPRO", event_type="DEMERGER")]
    )
    out = importer.transform_lineage_events(df)
    assert out.iloc[0]["change_reason"] == "merger"


def test_delisting_resolves_security_id_from_old_symbol(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="WIPRO", symbol_to=None, event_type="DELISTING")]
    )
    out = importer.transform_lineage_events(df)
    assert len(out) == 1
    assert out.iloc[0]["security_id"] == 3  # WIPRO → 3


def test_relisting_resolves_security_id_from_new_symbol_when_old_is_none(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from=None, symbol_to="TCS", event_type="RELISTING")]
    )
    out = importer.transform_lineage_events(df)
    assert len(out) == 1
    assert out.iloc[0]["security_id"] == 2  # TCS → 2


def test_reactivation_maps_to_relisting_enum(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from=None, symbol_to="TCS", event_type="REACTIVATION")]
    )
    out = importer.transform_lineage_events(df)
    assert out.iloc[0]["change_reason"] == "relisting"


def test_pipeline_extra_columns_dropped(importer):
    """confidence, reason, corroborating_evidence must not appear in output."""
    df = pd.DataFrame(
        [_lineage_row(symbol_from="INFY", symbol_to="TCS", event_type="MERGER")]
    )
    out = importer.transform_lineage_events(df)
    for col in (
        "confidence",
        "reason",
        "corroborating_evidence",
        "symbol_from",
        "symbol_to",
        "event_type",
        "event_date",
    ):
        assert col not in out.columns, f"unexpected column in output: {col}"


# ── edge cases ────────────────────────────────────────────────────────────────


def test_empty_dataframe_returns_empty(importer):
    df = pd.DataFrame(
        columns=[
            "symbol_from",
            "symbol_to",
            "event_date",
            "event_type",
            "confidence",
            "reason",
            "corroborating_evidence",
        ]
    )
    out = importer.transform_lineage_events(df)
    assert out.empty


def test_listing_rows_dropped(importer):
    """LISTING has no ENUM equivalent and must be silently dropped."""
    rows = [
        _lineage_row(symbol_from=None, symbol_to="INFY", event_type="LISTING"),
        _lineage_row(symbol_from="OLDNAME", symbol_to="TCS", event_type="RENAME"),
    ]
    out = importer.transform_lineage_events(pd.DataFrame(rows))
    assert len(out) == 1
    assert out.iloc[0]["change_reason"] == "rename"


def test_suspension_rows_dropped(importer):
    """SUSPENSION has no ENUM equivalent and must be silently dropped."""
    df = pd.DataFrame(
        [_lineage_row(symbol_from="INFY", symbol_to=None, event_type="SUSPENSION")]
    )
    out = importer.transform_lineage_events(df)
    assert out.empty


def test_unresolvable_symbol_rows_dropped(importer):
    """Rows whose symbol does not exist in dim_security_master must be dropped."""
    rows = [
        _lineage_row(symbol_from="UNKNOWN_SYM", symbol_to=None, event_type="DELISTING"),
        _lineage_row(symbol_from="WIPRO", symbol_to=None, event_type="DELISTING"),
    ]
    out = importer.transform_lineage_events(pd.DataFrame(rows))
    assert len(out) == 1
    assert out.iloc[0]["security_id"] == 3  # only WIPRO resolved


def test_multiple_rows_all_event_types(importer):
    """Smoke test: all valid event types round-trip without error."""
    valid_types = [k for k, v in _LINEAGE_EVENT_TYPE_MAP.items()]
    rows = [
        _lineage_row(symbol_from="OLDNAME", symbol_to="INFY", event_type=et)
        for et in valid_types
    ]
    out = importer.transform_lineage_events(pd.DataFrame(rows))
    assert not out.empty
    assert (
        out["change_reason"].isin(["rename", "merger", "delisting", "relisting"]).all()
    )


def test_security_id_is_integer(importer):
    df = pd.DataFrame(
        [_lineage_row(symbol_from="TCS", symbol_to="INFY", event_type="RENAME")]
    )
    out = importer.transform_lineage_events(df)
    assert out["security_id"].dtype in (int, "int64", "Int64")
