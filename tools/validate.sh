#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Deterministic pre-push validation for tickertruth's website/Worker side.
# Ported from the sibling truesignal project's tools/validate.sh pattern.
# No LLM involved — plain curl/grep checks against a running deployment.
#
# Scope: website/public/ (static assets) + src/index.js (the Worker) only.
# The Python/dolt data pipeline (extract/normalize/lineage/adjust/validate/
# load/export) has its own pytest-based validation — out of scope here.
#
# Usage:
#   tools/validate.sh [URL] [--email]
#   URL defaults to http://localhost:8787 (wrangler dev's default port). If
#   nothing is listening there yet, this script starts `npm run dev` itself,
#   waits for it to come up, and stops it again when the checks finish — it
#   never touches a dev server it didn't start (if one's already running on
#   that port, e.g. in another terminal, it's left alone). This self-managed
#   start/stop only happens for localhost/127.0.0.1 targets; a preview or
#   production URL is assumed to already be live and is never started here.
#
#   The /api/contact check is SKIPPED by default — it sends a real email
#   through Resend, which burns the free tier's send limit. Pass --email to
#   actually exercise it (e.g. right before a push, not on every local run).
#
#   /api/razorpay-webhook is NOT checked here: it requires a valid Razorpay
#   HMAC signature (RAZORPAY_WEBHOOK_SECRET) and only fires on a real
#   payment_link.paid event — there's no safe synthetic call to make against
#   it, so it's left to Razorpay's own webhook test tool / dashboard.
#
# Exit code 0 = every automatable check passed. Non-zero = at least one
# failed; see the FAIL lines above the summary for which.
#
# NOT covered here (needs a human/browser):
#   - Responsive check at any breakpoints in use
#   - Judgment on whether a broken external link should become plain text
# ---------------------------------------------------------------------------
set -uo pipefail

WITH_EMAIL=0
URL=""
for arg in "$@"; do
  case "$arg" in
    --email) WITH_EMAIL=1 ;;
    *) URL="$arg" ;;
  esac
done
URL="${URL:-http://localhost:8787}"
FAILED=0
DEV_PID=""

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; FAILED=1; }

cleanup() {
  if [ -n "$DEV_PID" ]; then
    kill "$DEV_PID" 2>/dev/null
    wait "$DEV_PID" 2>/dev/null
    # npm run dev's child (wrangler/miniflare) can outlive the npm process
    # itself, so make sure nothing's still bound to the port we used.
    local port="${URL##*:}"
    port="${port%%/*}"
    lsof -ti ":$port" 2>/dev/null | xargs -r kill 2>/dev/null
  fi
}
trap cleanup EXIT

# If we're targeting localhost and nothing's listening yet, start our own
# `npm run dev` for the duration of the checks.
case "$URL" in
  http://localhost:*|http://127.0.0.1:*)
    if ! curl -s -o /dev/null -m 2 "$URL/"; then
      echo "no dev server at $URL — starting 'npm run dev'..."
      npm run dev >/tmp/tickertruth-validate-dev.log 2>&1 &
      DEV_PID=$!
      for _ in $(seq 1 30); do
        curl -s -o /dev/null -m 2 "$URL/" && break
        sleep 1
      done
      if ! curl -s -o /dev/null -m 2 "$URL/"; then
        echo "dev server did not come up within 30s — see /tmp/tickertruth-validate-dev.log" >&2
        exit 1
      fi
      echo "dev server up (pid $DEV_PID) — will stop it when checks finish"
      echo
    fi
    ;;
esac

echo "== validating against $URL =="
echo

# 1. Every route returns 200
echo "-- routes --"
for p in / /pricing /methodology /sample-queries /release-notes /contact /blog/ \
         /robots.txt /sitemap.xml /security.txt /.well-known/security.txt; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$URL$p")
  if [ "$code" = "200" ]; then
    pass "$p -> $code"
  else
    fail "$p -> $code"
  fi
done
echo

# 2. Contact form API — the one real email-sending endpoint in src/index.js
#    (POST /api/contact, sends via Resend). Skipped by default since it
#    burns the free-tier send limit; pass --email to actually run it.
#    (There's also POST /api/razorpay-webhook, which sends a notification
#    email, but it requires a valid HMAC signature and only makes sense
#    against a real Razorpay event — not exercised here; see header note.)
echo "-- /api/contact --"
if [ "$WITH_EMAIL" -eq 1 ]; then
  resp=$(curl -s -m 10 -X POST "$URL/api/contact" -H "Content-Type: application/json" \
    -d '{"name":"Validate Script","email":"test@example.com","message":"automated check"}')
  if echo "$resp" | grep -q '"success":true'; then
    pass "/api/contact -> $resp"
  else
    fail "/api/contact -> $resp"
  fi
else
  echo "SKIP  /api/contact (pass --email to send a real test email via Resend)"
fi
echo

# 3. Dead internal links — every href="/..." target should resolve to a file
echo "-- internal links --"
LINK_FAILS=0
while IFS= read -r -d '' file; do
  while IFS= read -r target; do
    target="${target%%#*}"
    [ -z "$target" ] && target="/"
    if [ "$target" = "/" ]; then
      path="website/public/index.html"
    elif [[ "$target" == *.* ]]; then
      path="website/public${target}"
    elif [ -d "website/public${target}" ]; then
      path="website/public${target}/index.html"
    else
      path="website/public${target}.html"
    fi
    if [ ! -f "$path" ]; then
      fail "$file references \"$target\" -> no file at $path"
      LINK_FAILS=1
    fi
  done < <(grep -oE 'href="/[^"#]*' "$file" | sed 's/href="//' | sort -u)
done < <(find website/public -name '*.html' -print0)
[ "$LINK_FAILS" -eq 0 ] && pass "all internal links resolve"
echo

# 4. No secrets staged or present where they shouldn't be
echo "-- secrets --"
if git status --porcelain | grep -qE '(^|/)(\.dev\.vars|\.env|\.wrangler/|node_modules/|\.DS_Store)($|/| )'; then
  fail "git status shows .dev.vars/.env/.wrangler/node_modules/.DS_Store — review before committing"
  git status --porcelain | grep -E '(^|/)(\.dev\.vars|\.env|\.wrangler/|node_modules/|\.DS_Store)($|/| )'
else
  pass "no secret-like paths in git status"
fi
echo

echo "== summary =="
if [ "$FAILED" -eq 0 ]; then
  echo "all automatable checks passed."
  echo "still do by hand: responsive check across breakpoints in use, and eyeball any external links."
else
  echo "one or more checks FAILED — see above. Not safe to ship."
fi
exit $FAILED
