#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="tickertruth"
LOG_FILE="$(mktemp -t wrangler-del.XXXXXX.log)"
trap 'rm -f "$LOG_FILE"' EXIT

domains=$(npx wrangler pages project list --json | jq -r --arg name "$PROJECT_NAME" '.[] | select(."Project Name" == $name) | ."Project Domains"')
if [ -z "$domains" ]; then
  echo "Error: project '$PROJECT_NAME' not found." >&2
  exit 1
fi
if [ "$domains" != "${PROJECT_NAME}.pages.dev" ]; then
  echo "Error: '$PROJECT_NAME' has custom domain(s) mapped ($domains) — refusing to bulk-delete deployments." >&2
  exit 1
fi
echo "Confirmed '$PROJECT_NAME' only has the default pages.dev domain ($domains). Proceeding."

prod_id=""
while :; do
  ids=$(npx wrangler pages deployment list --project-name "$PROJECT_NAME" --json | jq -r '.[].Id')
  to_delete=$(echo "$ids" | grep -v -F -x "$prod_id" | grep .) || true
  [ -z "$to_delete" ] && { echo "Done. Production: $prod_id"; break; }
  echo "Deleting $(echo "$to_delete" | wc -l | tr -d ' ') deployments..."
  while IFS= read -r id; do
    if ! npx wrangler pages deployment delete "$id" --project-name "$PROJECT_NAME" --force 2>&1 | tee "$LOG_FILE" | grep -q "Successfully deleted"; then
      grep -q "active production deployment" "$LOG_FILE" && prod_id="$id" || true
    fi
  done <<< "$to_delete"
done