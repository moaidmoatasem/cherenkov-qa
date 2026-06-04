#!/usr/bin/env bash
# scripts/apply_branch_protection.sh — X2: Apply branch-protection ruleset on main (issue #131)
#
# REQUIRES: GitHub Personal Access Token with `repo` + `admin:repo_hook` scopes.
# The token must belong to a repository administrator.
#
# Usage:
#   bash scripts/apply_branch_protection.sh          # dry-run (prints ruleset JSON, no API call)
#   bash scripts/apply_branch_protection.sh --apply  # applies the ruleset via gh api
#
# Authority: docs/process/GITHUB_PM.md §5.
# Branch protection rules applied:
#   - Require PR before merge; ≥1 approving review; dismiss stale approvals on push
#   - Required status checks: Documentation Coverage, Healing Suggest-Only,
#                             CLI Help + Docs Gate, CodeQL
#   - Require conversation resolution before merge
#   - Require linear history (squash)
#   - Block force-push and deletion
# ----------------------------------------------------------------------------
set -euo pipefail

REPO="moaidmoatasem/cherenkov-qa"
BRANCH="main"
APPLY=false

if [[ "${1:-}" == "--apply" ]]; then
  APPLY=true
fi

# ── Required status check contexts (must match exact CI job names) ───────────
# These are the job `name:` fields from .github/workflows/ci.yml + codeql.yml
REQUIRED_CHECKS=(
  "Documentation Coverage"
  "Healing Suggest-Only"
  "CLI Help + Docs Gate"
  "CodeQL"
)

# Build required_status_checks JSON array
checks_json="["
for i in "${!REQUIRED_CHECKS[@]}"; do
  check="${REQUIRED_CHECKS[$i]}"
  if [ $i -gt 0 ]; then checks_json+=","; fi
  checks_json+="{\"context\":\"$check\"}"
done
checks_json+="]"

# ── Branch Protection Ruleset JSON ──────────────────────────────────────────
RULESET=$(cat <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": $(echo $checks_json | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps([x['context'] for x in d]))")
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "required_linear_history": true
}
EOF
)

echo "============================================================"
echo "  CHERENKOV — Branch Protection Script (X2, issue #131)"
echo "============================================================"
echo ""
echo "  Repository : $REPO"
echo "  Branch     : $BRANCH"
echo ""
if $APPLY; then
  echo "  MODE: APPLY — will call gh api to set branch protection"
else
  echo "  MODE: DRY-RUN — will print ruleset JSON only"
fi
echo ""
echo "  Ruleset to apply:"
echo "$RULESET" | python3 -m json.tool
echo ""

if $APPLY; then
  echo "Applying branch protection via gh api..."
  echo "$RULESET" | gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    "/repos/$REPO/branches/$BRANCH/protection" \
    --input -
  echo ""
  echo "[OK] Branch protection applied to $BRANCH."
  echo ""
  echo "Verify at: https://github.com/$REPO/settings/branches"
else
  echo "  (dry-run — no API calls made)"
  echo ""
  echo "  Prerequisites to run --apply:"
  echo "    1. gh auth login  (with a PAT that has admin:repo_hook + repo scope)"
  echo "    2. Confirm you are a repository administrator"
  echo "    3. bash scripts/apply_branch_protection.sh --apply"
  echo ""
  echo "  Alternatively, apply manually via:"
  echo "    GitHub → Settings → Branches → Add branch ruleset"
  echo "    (Settings → Branches UI maps 1-to-1 with this ruleset)"
fi
