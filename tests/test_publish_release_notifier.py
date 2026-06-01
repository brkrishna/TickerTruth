"""
Tests for ReleaseNotifier (BUG-6).

Covers:
- generate_release_notes() writes only to releases/monthly/
- update_changelog() skips when the run date is already present
- update_changelog() inserts when no prior entry exists
- update_changelog() creates the file from scratch if it doesn't exist
"""

import pytest
from datetime import date

from pipelines.publish.release_notifier import ReleaseNotifier


RUN_DATE = date(2026, 6, 1)
STATS = {
    "new_securities": 10,
    "new_actions": 5,
    "lineage_events": 2,
}


@pytest.fixture()
def notifier(tmp_path):
    return ReleaseNotifier(
        releases_dir=tmp_path / "releases" / "monthly",
        changelog=tmp_path / "docs" / "release-notes.md",
    )


# ── generate_release_notes ────────────────────────────────────────────────────

def test_generate_writes_to_releases_dir(notifier, tmp_path):
    path = notifier.generate_release_notes(RUN_DATE, STATS)
    assert path.exists()
    assert path.parent == tmp_path / "releases" / "monthly"
    assert path.name == "v2026.06.01.md"


def test_generate_does_not_touch_changelog(notifier):
    notifier.generate_release_notes(RUN_DATE, STATS)
    assert not notifier.changelog.exists()


def test_generate_content_includes_stats(notifier):
    path = notifier.generate_release_notes(RUN_DATE, STATS)
    content = path.read_text()
    assert "10" in content   # new_securities
    assert "5" in content    # new_actions
    assert "2" in content    # lineage_events


# ── update_changelog duplicate guard ─────────────────────────────────────────

def test_update_changelog_skips_when_date_already_present(notifier, tmp_path):
    """Second call for the same date must not add a duplicate entry."""
    notifier.changelog.parent.mkdir(parents=True, exist_ok=True)
    notifier.changelog.write_text(
        "# Release Notes\n\n"
        "### v2026.06.01 — 2026-06-01\n\n"
        "- 0 securities, 0 corporate actions, 0 lineage events\n\n"
    )

    notifier.update_changelog(RUN_DATE, STATS)

    content = notifier.changelog.read_text()
    assert content.count("2026-06-01") == 1, "duplicate entry written despite guard"


def test_update_changelog_inserts_when_date_absent(notifier, tmp_path):
    """A new date is prepended when it doesn't already appear in the file."""
    notifier.changelog.parent.mkdir(parents=True, exist_ok=True)
    notifier.changelog.write_text(
        "# Release Notes\n\n"
        "### v2026.05.01 — 2026-05-01\n\n"
        "- 0 securities, 0 corporate actions, 0 lineage events\n\n"
    )

    notifier.update_changelog(RUN_DATE, STATS)

    content = notifier.changelog.read_text()
    assert "2026-06-01" in content
    assert "2026-05-01" in content


def test_update_changelog_creates_file_when_missing(notifier):
    """If the changelog doesn't exist yet, create it."""
    assert not notifier.changelog.exists()
    notifier.changelog.parent.mkdir(parents=True, exist_ok=True)

    notifier.update_changelog(RUN_DATE, STATS)

    assert notifier.changelog.exists()
    assert "2026-06-01" in notifier.changelog.read_text()


def test_update_changelog_new_entry_appears_before_older_entries(notifier):
    """Newer entries should appear above older ones (most-recent-first order)."""
    notifier.changelog.parent.mkdir(parents=True, exist_ok=True)
    notifier.changelog.write_text(
        "# Release Notes\n\n"
        "### v2026.05.01 — 2026-05-01\n\n"
        "- 0 securities, 0 corporate actions, 0 lineage events\n\n"
    )

    notifier.update_changelog(RUN_DATE, STATS)

    content = notifier.changelog.read_text()
    june_pos = content.index("2026-06-01")
    may_pos  = content.index("2026-05-01")
    assert june_pos < may_pos, "newer entry should appear before older entry"
