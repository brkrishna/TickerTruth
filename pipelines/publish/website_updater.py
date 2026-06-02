"""
WebsiteUpdater — parses a versioned release notes MD file and injects a
matching HTML card into website/landing-page/release-notes.html.

Idempotent: skips injection if a card for the version already exists.

CLI usage:
    python pipelines/publish/website_updater.py --date 2026-06-30
    python pipelines/publish/website_updater.py --md releases/monthly/v2026.06.30.md
"""

import argparse
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT       = Path(__file__).parent.parent.parent
RELEASES_DIR       = PROJECT_ROOT / "releases" / "monthly"
RELEASE_NOTES_HTML = PROJECT_ROOT / "website" / "landing-page" / "release-notes.html"

# Exact string in the HTML after which new cards are prepended.
_INJECTION_MARKER = "    <h2>Latest Releases</h2>"

# HTML comment tag embedded in every generated card; used to detect duplicates.
_CARD_TAG = "<!-- release:{version} -->"


# ── public API ────────────────────────────────────────────────────────────────

class WebsiteUpdater:
    def __init__(
        self,
        html_path: Path = RELEASE_NOTES_HTML,
        releases_dir: Path = RELEASES_DIR,
    ):
        self.html_path    = Path(html_path)
        self.releases_dir = Path(releases_dir)

    def update_for_date(self, run_date: date) -> bool:
        """Locate the MD for run_date, parse it, and inject the card.

        Returns True if the HTML was modified, False if already up to date.
        """
        version = f"v{run_date.strftime('%Y.%m.%d')}"
        md_path = self.releases_dir / f"{version}.md"
        if not md_path.exists():
            logger.warning("[website] Release notes not found: %s", md_path)
            return False
        return self.update_from_md(md_path)

    def update_from_md(self, md_path: Path) -> bool:
        """Parse MD at md_path and inject card into HTML.

        Returns True if the HTML was modified.
        Raises ValueError if the HTML injection marker is missing.
        """
        data    = _parse_release_md(md_path)
        version = data["version"]
        tag     = _CARD_TAG.format(version=version)

        html = self.html_path.read_text(encoding="utf-8")
        if tag in html:
            logger.info("[website] Card for %s already present — skipping", version)
            return False

        card = _build_card_html(data)
        html = _inject_card(html, card)
        self.html_path.write_text(html, encoding="utf-8")
        logger.info("[website] Injected card for %s → %s", version, self.html_path.name)
        return True


# ── MD parser ─────────────────────────────────────────────────────────────────

def _parse_release_md(path: Path) -> dict:
    """
    Parse a ReleaseNotifier-generated MD file into a structured dict:

        {
            "version":      "v2026.06.02",
            "released":     "2026-06-02",
            "dolt_commit":  "abc123" | "N/A",
            "stats": {
                "new_securities": int,
                "updated_securities": int,
                "new_actions": int,
                "lineage_events": int,
                "adjustment_rows": int,
            },
            "sections": {
                "Summary":          [...bullet strings...],
                "Data Changes":     [...],
                "Quality Warnings": [...],  # may be absent
                "Known Issues":     [...],
                "Next Release":     [...],
            },
        }
    """
    text  = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    data: dict = {
        "version":     "",
        "released":    "",
        "dolt_commit": "",
        "stats":       {},
        "sections":    {},
    }

    # Title: "# Release v2026.06.02"
    if lines and lines[0].startswith("# Release "):
        data["version"] = lines[0].split("# Release ", 1)[1].strip()

    # Metadata lines before the first "## " heading
    for line in lines[1:]:
        if line.startswith("## "):
            break
        m = re.match(r"\*\*Released:\*\*\s*(.+)", line)
        if m:
            data["released"] = m.group(1).strip()
            continue
        m = re.match(r"\*\*Dolt Commit:\*\*\s*(.+)", line)
        if m:
            data["dolt_commit"] = m.group(1).strip()

    # Section bodies — collect "- " bullets under each "## Heading"
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            data["sections"][current] = []
        elif current is not None and line.startswith("- "):
            data["sections"][current].append(line[2:].strip())

    # Parse Summary bullets into integer stats
    _STAT_KEYS = {
        "New securities":             "new_securities",
        "Updated securities":         "updated_securities",
        "Corporate actions ingested": "new_actions",
        "Lineage events detected":    "lineage_events",
        "Adjustment factor rows":     "adjustment_rows",
    }
    for bullet in data["sections"].get("Summary", []):
        m = re.match(r"\*\*(.+?):\*\*\s*([\d,]+)", bullet)
        if m:
            label = m.group(1).strip()
            if label in _STAT_KEYS:
                try:
                    data["stats"][_STAT_KEYS[label]] = int(m.group(2).replace(",", ""))
                except ValueError:
                    data["stats"][_STAT_KEYS[label]] = 0

    return data


# ── HTML card builder ─────────────────────────────────────────────────────────

def _build_card_html(data: dict) -> str:
    """Render parsed MD data as an HTML release card (8-space indented, matches page)."""

    version  = data["version"]
    released = data["released"]
    stats    = data["stats"]
    sections = data["sections"]

    def fmt(n: int) -> str:
        return f"{n:,}" if n else "0"

    new_sec  = stats.get("new_securities",  0)
    new_act  = stats.get("new_actions",     0)
    lin_ev   = stats.get("lineage_events",  0)
    adj_rows = stats.get("adjustment_rows", 0)

    def _li(text: str) -> str:
        # Convert **bold** markers to <strong> tags for inline display
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return f"            <li>{html}</li>"

    def _section(title: str, bullets: list[str], extra_class: str = "") -> str:
        if not bullets:
            return ""
        css = f'class="release-section {extra_class}"' if extra_class else 'class="release-section"'
        items = "\n".join(_li(b) for b in bullets)
        return (
            f'        <div {css}>\n'
            f'          <h3>{title}</h3>\n'
            f'          <ul>\n'
            f'{items}\n'
            f'          </ul>\n'
            f'        </div>'
        )

    body_parts = [
        _section("Data Changes",     sections.get("Data Changes",     [])),
        _section("Quality Warnings", sections.get("Quality Warnings", [])),
        _section("Known Issues",     sections.get("Known Issues",     []), "known-issues"),
        _section("Next Release",     sections.get("Next Release",     []), "next-release"),
    ]
    body_html = "\n".join(p for p in body_parts if p)

    # "v2026.06.02" → "2026-06-02"
    display_version = version.lstrip("v").replace(".", "-")

    tag = _CARD_TAG.format(version=version)

    return (
        f"    {tag}\n"
        f'    <div class="release">\n'
        f'      <div class="release-header">\n'
        f'        <div>\n'
        f'          <h2>Release {display_version}</h2>\n'
        f'          <div class="release-date">Released {released}</div>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div class="release-stats">\n'
        f'        <div class="stat">\n'
        f'          <div class="stat-val">{fmt(new_sec)}</div>\n'
        f'          <div class="stat-label">Securities</div>\n'
        f'        </div>\n'
        f'        <div class="stat">\n'
        f'          <div class="stat-val">{fmt(new_act)}</div>\n'
        f'          <div class="stat-label">Corp. Actions</div>\n'
        f'        </div>\n'
        f'        <div class="stat">\n'
        f'          <div class="stat-val">{fmt(lin_ev)}</div>\n'
        f'          <div class="stat-label">Lineage Events</div>\n'
        f'        </div>\n'
        f'        <div class="stat">\n'
        f'          <div class="stat-val">{fmt(adj_rows)}</div>\n'
        f'          <div class="stat-label">Adj. Factors</div>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div class="release-body">\n'
        f'{body_html}\n'
        f'      </div>\n'
        f'    </div>\n'
    )


# ── injector ──────────────────────────────────────────────────────────────────

def _inject_card(html: str, card: str) -> str:
    """
    Prepend card after the _INJECTION_MARKER line in html.

    Raises ValueError if the marker is not found — which means the HTML
    template has been restructured and needs a manual check.
    """
    idx = html.find(_INJECTION_MARKER)
    if idx == -1:
        raise ValueError(
            f"Injection marker not found in HTML.\n"
            f"Expected line: {_INJECTION_MARKER!r}\n"
            f"Check website/landing-page/release-notes.html."
        )
    end_of_marker_line = html.index("\n", idx) + 1
    return html[:end_of_marker_line] + "\n" + card + html[end_of_marker_line:]


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="website_updater.py",
        description="Inject a release card into release-notes.html from a dated MD file.",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Run date; locates releases/monthly/vYYYY.MM.DD.md automatically.",
    )
    group.add_argument(
        "--md",
        metavar="PATH",
        help="Explicit path to a release notes MD file.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args    = _parse_args(argv)
    updater = WebsiteUpdater()

    try:
        if args.date:
            run_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            changed  = updater.update_for_date(run_date)
        else:
            changed = updater.update_from_md(Path(args.md))
    except (ValueError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1

    return 0 if changed or args.date else 0


if __name__ == "__main__":
    sys.exit(main())
