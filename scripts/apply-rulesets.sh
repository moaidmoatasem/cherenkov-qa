#!/usr/bin/env bash
# Apply GitHub repository rulesets from .github/rulesets/*.json
#
# Requirements: a Personal Access Token with `administration:write` scope.
#
# Usage:
#   export GITHUB_PAT=ghp_...
#   bash scripts/apply-rulesets.sh
#
# To remove existing rulesets before re-applying, set PURGE_EXISTING=1:
#   PURGE_EXISTING=1 bash scripts/apply-rulesets.sh

set -euo pipefail

OWNER="moaidmoatasem"
REPO="cherenkov-qa"
TOKEN="${GITHUB_PAT:-${GITHUB_TOKEN:-}}"
API="https://api.github.com/repos/${OWNER}/${REPO}/rulesets"

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: set GITHUB_PAT (needs administration:write scope)" >&2
  exit 1
fi

auth_header="Authorization: Bearer ${TOKEN}"

if [[ "${PURGE_EXISTING:-0}" == "1" ]]; then
  echo "Purging existing rulesets..."
  existing=$(curl -sf -H "$auth_header" -H "Accept: application/vnd.github+json" "$API" | \
    python3 -c "import sys,json; [print(r['id']) for r in json.load(sys.stdin)]")
  for id in $existing; do
    curl -sf -X DELETE -H "$auth_header" -H "Accept: application/vnd.github+json" "${API}/${id}"
    echo "  Deleted ruleset $id"
  done
fi

for file in .github/rulesets/*.json; do
  name=$(python3 -c "import json; print(json.load(open('${file}'))['name'])")
  echo "Applying: ${file} (\"${name}\")..."
  response=$(curl -sf -X POST \
    -H "$auth_header" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    "$API" \
    --data-binary "@${file}" 2>&1) || {
      echo "  FAILED: $response" >&2
      exit 1
    }
  id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  echo "  Created ruleset id=${id}"
done

echo "Done."
