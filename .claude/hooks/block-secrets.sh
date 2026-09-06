#!/usr/bin/env bash
# PreToolUse hook — blocks writes that would commit a secret to disk.
#
# Fires BEFORE the tool runs, so a bad write never happens rather than
# being caught afterwards. This project talks to the Resend API and
# Razorpay from a Worker (src/index.js) using env.RESEND_API_KEY /
# env.RAZORPAY_WEBHOOK_SECRET — those keys, or any other credential,
# must never land in a source file.
#
# Deliberately narrow: it looks for high-confidence key shapes, not any
# string containing "password". False positives here are expensive because
# they interrupt real work, so the patterns stay specific.

set -uo pipefail

PAYLOAD=$(cat)

CONTENT=$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
parts = []
for k in ("content", "new_string", "new_str"):
    if ti.get(k):
        parts.append(str(ti[k]))
print("\n".join(parts))
' 2>/dev/null)

[ -z "$CONTENT" ] && exit 0

FOUND=""

check() {
  # -e is required: patterns starting with '-' are otherwise parsed as flags.
  if printf '%s' "$CONTENT" | grep -qiE -e "$1"; then
    FOUND="${FOUND}  - $2\n"
  fi
}

check 're_[a-zA-Z0-9]{20,}'                        "Resend API key"
check 'sk-ant-[a-zA-Z0-9_-]{20,}'                  "Anthropic API key"
check 'sk-[a-zA-Z0-9]{32,}'                        "OpenAI-style API key"
check 'ghp_[a-zA-Z0-9]{30,}'                       "GitHub personal access token"
check 'AKIA[0-9A-Z]{16}'                           "AWS access key ID"
check 'CF[A-Za-z0-9_-]{30,}'                       "Possible Cloudflare API token"
check '-----BEGIN [A-Z ]*PRIVATE KEY-----'         "Private key block"
check '(password|passwd|secret|api_key|apikey|token)\s*[:=]\s*["'"'"'][^"'"'"'{}$ ]{8,}["'"'"']' \
                                                   "Hardcoded credential literal"

if [ -n "$FOUND" ]; then
  {
    echo "BLOCKED: this write appears to contain a secret."
    echo ""
    printf "%b" "$FOUND"
    echo ""
    echo "Do not write credentials into source files. Use env bindings"
    echo "(wrangler secrets / .dev.vars, which is already gitignored) and"
    echo "read them from the Worker's env parameter instead."
  } >&2
  exit 2
fi

exit 0
