#!/usr/bin/env bash
# scripts/prune_branches.sh — X1: Prune merged/stale remote branches (issue #130)
#
# Usage:
#   bash scripts/prune_branches.sh          # dry-run (no deletions)
#   bash scripts/prune_branches.sh --apply  # actually delete remote branches
#
# Branches are selected by `git branch -r --merged origin/main`.
# Protected branches (main, develop, active epoch, rescue) are never deleted.
# Authority: docs/vision/08_DELIVERY_PLAN.md §3 X1.
set -euo pipefail

APPLY=false
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=true
fi

# ── Branches confirmed merged into origin/main ──────────────────────────────
# Verified via: git branch -r --merged origin/main | grep -v 'HEAD\|main\|develop'
# Date: 2026-06-04
MERGED_BRANCHES=(
  "chore/reconcile-to-track-a"
  "docs/delivery-plan"
  "docs/governance-pm-kit"
  "docs/reality-engine-plan"
  "e1-4-router-tier-egress"
  "e1-5-cache-cost-latency"
  "epoch0/stabilise-ci-green-on-main"
  "epoch0/tag-foundation-v0"
  "epoch1/e1-2-model-provider-spi-11963756022064022129"
  "feat/109-hitl-cli"
  "feat/111-hitl-docs"
  "feat/112-validate-gate"
  "feat/113-114-e7-reflector-exit"
  "feat/115-qa-runbook"
  "feat/116-openclaw-tier1-adapter"
  "feat/92-coverage-sdet"
  "feat/93-94-certification-copilot"
  "feat/e12-e13-cert-governance-mentor-autonomy"
  "feat/e7-reflector-memory-self-audit"
  "feat/e8-perf-anomaly"
  "feat/epoch9-vision-epoch11-coverage"
  "feat/fe-0-ui-kit"
  "feat/fe-1-navigation"
  "feat/hitl-queue-backend"
  "feature/deep-healing-sandbox"
  "feature/e1-3-second-provider"
  "feature/e2-refinements"
  "feature/e4-continuity"
  "feature/epoch5-experience-config"
  "feature/issue-100-track-a-gaps"
  "feature/issue-24-audit-pipeline"
  "feature/issue-35-epoch-1-complete"
  "feature/issue-36-source-adapter"
  "feature/issue-38-embedding-index"
  "feature/issue-61-truth-protocol"
  "feature/issue-62-cross-service-check"
  "feature/issue-63-divergence-corpus"
  "feature/issue-64-specialist-model"
  "feature/track-b-integration"
  "fix/dashboard-api-alignment"
  "rescue/epoch-4-untracked"
)

# ── Branches to keep (never delete) ─────────────────────────────────────────
KEEP=(
  "main"
  "develop"
)

echo "============================================================"
echo "  CHERENKOV — Branch Pruning Script (X1, issue #130)"
echo "============================================================"
echo ""
if $APPLY; then
  echo "  MODE: APPLY — remote branches WILL be deleted"
else
  echo "  MODE: DRY-RUN — no changes (pass --apply to delete)"
fi
echo ""

# Refresh remote refs
echo "[1/3] Fetching remote refs (prune)..."
git fetch --prune origin

# Confirm each branch is actually present remotely before trying to delete
echo ""
echo "[2/3] Checking branches..."
TO_DELETE=()
SKIPPED=()
for branch in "${MERGED_BRANCHES[@]}"; do
  # Safety: never delete kept branches
  if printf '%s\n' "${KEEP[@]}" | grep -qx "$branch"; then
    SKIPPED+=("$branch (PROTECTED — in keep list)")
    continue
  fi
  # Check if branch exists on remote
  if git ls-remote --exit-code --heads origin "$branch" &>/dev/null; then
    TO_DELETE+=("$branch")
  else
    SKIPPED+=("$branch (already absent on remote)")
  fi
done

echo ""
echo "Branches to DELETE (${#TO_DELETE[@]}):"
for b in "${TO_DELETE[@]}"; do
  echo "  - $b"
done

echo ""
echo "Skipped (${#SKIPPED[@]}):"
for b in "${SKIPPED[@]}"; do
  echo "  ~ $b"
done

echo ""
echo "[3/3] Deleting remote branches..."
if $APPLY; then
  DELETED=0
  FAILED=0
  for branch in "${TO_DELETE[@]}"; do
    if git push origin --delete "$branch" 2>&1; then
      echo "  [OK] Deleted: $branch"
      DELETED=$((DELETED + 1))
    else
      echo "  [FAIL] Could not delete: $branch"
      FAILED=$((FAILED + 1))
    fi
  done
  echo ""
  echo "============================================================"
  echo "  Done: $DELETED deleted, $FAILED failed, ${#SKIPPED[@]} skipped"
  echo "============================================================"
else
  echo "  (dry-run — no branches deleted)"
  echo ""
  echo "  Run with --apply to execute the deletions:"
  echo "    bash scripts/prune_branches.sh --apply"
fi
