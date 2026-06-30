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
  existing_json=$(curl -sSf -H "$auth_header" -H "Accept: application/vnd.github+json" "$API") || {
    echo "ERROR: failed to list rulesets (check token scope)" >&2
    exit 1
  }
  while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    curl -sSf -X DELETE -H "$auth_header" -H "Accept: application/vnd.github+json" "${API}/${id}" >/dev/null
    echo "  Deleted ruleset $id"
  done < <(echo "$existing_json" | python3 -c "import sys,json; [print(r['id']) for r in json.load(sys.stdin)]")
fi

shopt -s nullglob
files=(.github/rulesets/*.json)
shopt -u nullglob
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No ruleset files found in .github/rulesets/ — nothing to apply."
  exit 0
fi

for file in "${files[@]}"; do
  name=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['name'])" "$file")
  echo "Applying: ${file} (\"${name}\")..."
  response=$(curl -sSf -X POST \
    -H "$auth_header" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    "$API" \
    --data-binary "@${file}") || {
      echo "  FAILED — see curl error above" >&2
      exit 1
    }
  id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  echo "  Created ruleset id=${id}"
done

echo "Done."
