#!/usr/bin/env bash
# PostToolUse hook — lint + project-specific sanity checks after an edit.
#
# Two tiers:
#   1. ESLint  — any edited .js file under src/, website/public/, or
#                tests/ (matches the `files` globs in eslint.config.js)
#   2. Sitemap — a new top-level page under website/public/ that isn't
#                listed in website/public/sitemap.xml is easy to forget;
#                flagged as a non-blocking notice, not an error (partials/
#                drafts are legitimately not meant to be indexed, and the
#                blog has its own generated sitemap).

set -uo pipefail
cd "$CLAUDE_PROJECT_DIR" || exit 0

PAYLOAD=$(cat)

FILE_PATH=$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
for k in ("file_path", "path"):
    if ti.get(k):
        print(ti[k]); break
' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

PROBLEMS=""

case "$FILE_PATH" in
  *.js)
    case "$FILE_PATH" in
      *"/src/"*|src/*|*"/website/public/"*|website/public/*|*"/tests/"*|tests/*|*.config.js)
        if [ -x "node_modules/.bin/eslint" ]; then
          LINT=$(npx --no-install eslint "$FILE_PATH" 2>&1)
          if [ $? -ne 0 ]; then
            PROBLEMS="${PROBLEMS}ESLint issues in ${FILE_PATH}:
${LINT}

"
          fi
        fi
        ;;
    esac
    ;;
esac

if [ -n "$PROBLEMS" ]; then
  {
    printf '%s' "$PROBLEMS"
    echo "Fix these before continuing."
  } >&2
  exit 2
fi

# --- Sitemap sanity (non-blocking) --------------------------------------
case "$FILE_PATH" in
  *"/website/public/"*.html|website/public/*.html)
    BASENAME=$(basename "$FILE_PATH")
    case "$FILE_PATH" in
      *"/website/public/blog/"*|website/public/blog/*)
        ;; # blog pages have their own generated sitemap, not the site one
      *)
        case "$BASENAME" in
          404.html) ;; # deliberately not indexed
          *)
            if [ -f "website/public/sitemap.xml" ] && ! grep -q "$BASENAME" website/public/sitemap.xml; then
              echo "Notice: ${BASENAME} isn't listed in website/public/sitemap.xml. If this is a real page, add it there (and to the shared nav markup, per CLAUDE.md's SEO section if one exists)." >&2
            fi
            ;;
        esac
        ;;
    esac
    ;;
esac

exit 0
