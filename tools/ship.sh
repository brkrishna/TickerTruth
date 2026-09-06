#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Deterministic validate -> commit -> push for tickertruth's website/Worker
# side. No LLM involved.
#
# Usage:
#   tools/ship.sh "<commit message>" [URL]
#
# URL defaults to http://localhost:8787 (run `npm run dev` first, or let
# tools/validate.sh start it for you). Runs tools/validate.sh against it;
# only commits and pushes if every automatable check passes.
#
# Scope: this only validates the website/Worker side (tools/validate.sh's
# scope) — it does not run the Python data-pipeline's pytest suite. Don't use
# this for pipeline-only commits; run the pipeline's own tests first.
#
# Only stages already-tracked, modified/deleted files (`git add -u`) — new
# files are never auto-staged, so an untracked secret or stray file can't get
# swept in silently. Add new files yourself first if this commit should
# include them.
# ---------------------------------------------------------------------------
set -uo pipefail

MSG="${1:-}"
URL="${2:-http://localhost:8787}"

if [ -z "$MSG" ]; then
  echo "usage: tools/ship.sh \"<commit message>\" [URL]" >&2
  exit 1
fi

echo "== pre-flight =="
if [ -z "$(git status --porcelain)" ]; then
  echo "nothing to commit — working tree is clean."
  exit 0
fi

UNTRACKED=$(git status --porcelain | grep '^??' | sed 's/^?? //')
if [ -n "$UNTRACKED" ]; then
  echo "untracked files NOT staged (add explicitly with 'git add <file>' first if they belong in this commit):"
  echo "$UNTRACKED" | sed 's/^/  /'
  echo
fi

echo "== validate =="
if ! tools/validate.sh "$URL"; then
  echo
  echo "validation failed — not committing or pushing." >&2
  exit 1
fi

echo
echo "== staging (tracked changes only) =="
git add -u
git status --short

if git diff --cached --quiet; then
  echo "nothing staged after 'git add -u' — if this commit needs new files, add them and rerun."
  exit 0
fi

echo
echo "== commit =="
git commit -m "$MSG"

BRANCH=$(git branch --show-current)
if [ -z "$BRANCH" ]; then
  echo "detached HEAD — not pushing. Check out a branch first." >&2
  exit 1
fi

echo
echo "== push =="
git push origin "$BRANCH"
