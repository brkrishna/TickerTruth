#!/usr/bin/env bash
# PostToolUse hook — runs the fast Vitest unit suite after any edit under
# src/ or tests/unit/.
#
# Fires automatically; not something the model chooses to do. This is
# what makes "run tests after every change" a guarantee instead of
# something that gets skipped under time pressure.
#
# Deliberately scoped to the unit suite (Vitest against the Workers
# runtime via @cloudflare/vitest-pool-workers, no browser) — it's fast
# enough to run on every edit. The Playwright e2e suite spins up a real
# browser against a running Worker, so it stays a manual step
# (`npm run test:e2e`) rather than a hook.
#
# Exit codes:
#   0 = pass through silently
#   2 = block / surface stderr back to Claude as feedback it must address

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

case "$FILE_PATH" in
  *"/src/"*|src/*|*"/tests/unit/"*|tests/unit/*) ;;
  *) exit 0 ;;
esac

if [ ! -x "node_modules/.bin/vitest" ]; then
  echo "test-on-edit hook: vitest not found — run 'npm install' first." >&2
  exit 0
fi

OUTPUT=$(npx --no-install vitest run 2>&1)
STATUS=$?

if [ $STATUS -ne 0 ]; then
  {
    echo "Unit tests FAILED after editing ${FILE_PATH}."
    echo ""
    echo "$OUTPUT" | tail -n 40
    echo ""
    echo "Fix this before continuing to the next step. Do not proceed with"
    echo "further edits while the suite is red."
  } >&2
  exit 2
fi

exit 0
