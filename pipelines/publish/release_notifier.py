"""
ReleaseNotifier — generates structured release notes and updates the changelog.
"""

import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
RELEASES_DIR = PROJECT_ROOT / "releases" / "monthly"
CHANGELOG    = PROJECT_ROOT / "docs" / "release-notes.md"


class ReleaseNotifier:
    """
    Writes versioned release notes and appends an entry to the changelog.

    Usage:
        notifier = ReleaseNotifier()
        path = notifier.generate_release_notes(date.today(), stats)
        notifier.update_changelog(date.today(), stats)
    """

    def __init__(
        self,
        releases_dir: Path = RELEASES_DIR,
        changelog:    Path = CHANGELOG,
    ):
        self.releases_dir = Path(releases_dir)
        self.changelog    = Path(changelog)

    def generate_release_notes(
        self,
        run_date: date,
        stats: dict,
    ) -> Path:
        """
        Write a versioned release notes file to releases/monthly/.

        Args:
            run_date: Release date
            stats: Dict with optional keys:
                   new_securities (int), updated_securities (int),
                   new_actions (int), lineage_events (int),
                   adjustment_rows (int), quality_warnings (list[str]),
                   known_issues (list[str]), dolt_commit (str)

        Returns:
            Path to the written release notes file.
        """
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        version  = f"v{run_date.strftime('%Y.%m.%d')}"
        out_path = self.releases_dir / f"{version}.md"

        new_sec  = stats.get("new_securities",     0)
        upd_sec  = stats.get("updated_securities", 0)
        new_act  = stats.get("new_actions",        0)
        lin_ev   = stats.get("lineage_events",     0)
        adj_rows = stats.get("adjustment_rows",    0)
        warnings = stats.get("quality_warnings",   [])
        issues   = stats.get("known_issues",       [])
        commit   = stats.get("dolt_commit",        "")

        lines = [
            f"# Release {version}",
            "",
            f"**Released:** {run_date.isoformat()}",
            f"**Dolt Commit:** {commit or 'N/A'}",
            "",
            "## Summary",
            "",
            f"- **New securities:** {new_sec:,}",
            f"- **Updated securities:** {upd_sec:,}",
            f"- **Corporate actions ingested:** {new_act:,}",
            f"- **Lineage events detected:** {lin_ev:,}",
            f"- **Adjustment factor rows:** {adj_rows:,}",
            "",
            "## Data Changes",
            "",
        ]

        if new_sec:
            lines.append(f"- Added {new_sec:,} new securities to dim_security_master")
        if new_act:
            lines.append(f"- Ingested {new_act:,} corporate action events")
        if lin_ev:
            lines.append(f"- Detected {lin_ev:,} symbol lineage events (renames, delistings, mergers)")
        if adj_rows:
            lines.append(f"- Computed {adj_rows:,} adjustment factor rows")

        if warnings:
            lines += ["", "## Quality Warnings", ""]
            for w in warnings:
                lines.append(f"- {w}")

        if issues:
            lines += ["", "## Known Issues", ""]
            for issue in issues:
                lines.append(f"- {issue}")
        else:
            lines += ["", "## Known Issues", "", "- None for this release"]

        lines += [
            "",
            "## Next Release",
            "",
            "- Planned: ongoing data refresh and quality improvements",
        ]

        out_path.write_text("\n".join(lines) + "\n")
        logger.info("Release notes written → %s", out_path)
        return out_path

    def update_changelog(self, run_date: date, stats: dict) -> None:
        """
        Prepend a summary entry to docs/release-notes.md (most recent first).

        Reads the existing file, inserts the new entry after the header,
        and rewrites the file.
        """
        version  = f"v{run_date.strftime('%Y.%m.%d')}"
        new_act  = stats.get("new_actions", 0)
        new_sec  = stats.get("new_securities", 0)
        lin_ev   = stats.get("lineage_events", 0)

        new_entry = "\n".join([
            f"### {version} — {run_date.isoformat()}",
            "",
            f"- {new_sec:,} securities, {new_act:,} corporate actions, "
            f"{lin_ev:,} lineage events",
            "",
        ])

        if self.changelog.exists():
            existing = self.changelog.read_text()
            # Insert after the first-level heading block (first blank line after #)
            lines     = existing.splitlines(keepends=True)
            insert_at = 0
            for i, line in enumerate(lines):
                if i > 0 and line.strip() == "" and lines[i - 1].startswith("#"):
                    insert_at = i + 1
                    break
            lines.insert(insert_at, new_entry + "\n")
            self.changelog.write_text("".join(lines))
        else:
            self.changelog.write_text(
                "# Release Notes\n\n" + new_entry
            )

        logger.info("Changelog updated → %s", self.changelog)
