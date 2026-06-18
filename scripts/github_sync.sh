#!/usr/bin/env bash
# CHERENKOV — GitHub PM sync (idempotent).
# Ensures labels + milestones, closes done E0–E4/E6-4 implementation tasks,
# and creates the validation-gate epic + gated backlog (E7–E13, FE).
#
# Authority: docs/process/GITHUB_PM.md. Safe by default (dry-run).
#   bash scripts/github_sync.sh                 # preview only, no mutations
#   bash scripts/github_sync.sh --apply         # create labels/milestones/issues
#   bash scripts/github_sync.sh --apply --close-done   # also close done E0–E4/E6-4 tasks
#
# Requires: gh (authenticated). Never deletes anything.
set -euo pipefail

REPO="moaidmoatasem/cherenkov-qa"
APPLY=0; CLOSE_DONE=0
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --close-done) CLOSE_DONE=1 ;;
    *) echo "unknown arg: $a"; exit 2 ;;
  esac
done
run() { if [ "$APPLY" = 1 ]; then echo "+ $*"; "$@"; else echo "DRY  $*"; fi; }

command -v gh >/dev/null || { echo "ERROR: gh not installed. See docs/process/GITHUB_PM.md §7"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "ERROR: gh not authenticated. Run: gh auth login"; exit 1; }

echo "== 1. Labels =="
ensure_label() { # name color desc
  if gh label list -R "$REPO" --limit 200 | grep -q "^$1[[:space:]]"; then echo "   ok: $1";
  else run gh label create "$1" -R "$REPO" --color "$2" --description "$3" || true; fi
}
ensure_label "type:epic"     "6f42c1" "Milestone-sized work"
ensure_label "type:task"     "0e8a16" "One shippable PR"
ensure_label "type:bug"      "d73a4a" "Defect in Track A"
ensure_label "type:docs"     "0075ca" "Documentation"
ensure_label "type:chore"    "fef2c0" "Maintenance"
ensure_label "type:research" "c5def5" "Spike / research"
ensure_label "priority:P0-critical" "b60205" "Drop everything"
ensure_label "priority:P1"   "d93f0b" "High"
ensure_label "priority:P2"   "fbca04" "Normal"
ensure_label "priority:P3"   "c2e0c6" "Low"
ensure_label "status:ready"        "ededed" "Ready to start"
ensure_label "status:in-progress"  "1d76db" "In progress"
ensure_label "status:in-review"    "fbca04" "In review"
ensure_label "status:blocked"      "000000" "Blocked"
ensure_label "blocked:validation-gate" "5319e7" "Blocked until Track A 5-QA gate passes"
ensure_label "do-not-extend-until-gate" "b60205" "Quarantined surface; no work pre-gate"
ensure_label "agent-ready"   "0e8a16" "Crisp acceptance, no human-only steps"
ensure_label "needs-human"   "d4c5f9" "Requires a human/owner"
for a in substrate truth divergence artifact continuity healing perf visual frontend ci security; do
  ensure_label "area:$a" "bfdadc" "Area: $a"; done

echo "== 2. Milestones =="
ensure_ms() {
  if gh api "repos/$REPO/milestones?state=all" --jq '.[].title' | grep -qx "$1"; then echo "   ok: $1";
  else run gh api "repos/$REPO/milestones" -f title="$1" -f description="$2" >/dev/null || true; fi
}
ensure_ms "M0 · Ship Track A"        "Pass the 5-QA validation gate"
ensure_ms "M1 · Foundation hardened" "Prove substrate/truth/divergence on a real OSS target"
ensure_ms "M2 · Reflector"           "E7 verdict memory / learning loop"
ensure_ms "M3 · Signals"             "E8 perf + E9 vision"
ensure_ms "M4 · Author & Trust"      "E10 Copilot, E11 SDET, E12 governance"
ensure_ms "M5 · Pairing & FE"        "E13 pairing + dashboard redesign"

echo "== 3. Close-candidates (implemented; see git history) =="
# Match open issues whose title starts with a done prefix.
DONE_RE='^E0-[123]|^E1-[1-6]|^E2-[1-6]|^E3-[1-5]|^E4-[1-5]|^E6-4'
gh issue list -R "$REPO" --state open --limit 300 --json number,title \
  --jq '.[] | "\(.number)\t\(.title)"' | grep -E "	($DONE_RE)" || echo "   (none matched / verify manually)"
if [ "$CLOSE_DONE" = 1 ]; then
  gh issue list -R "$REPO" --state open --limit 300 --json number,title \
    --jq '.[] | select(.title|test("'"$DONE_RE"'")) | .number' | while read -r n; do
      run gh issue close "$n" -R "$REPO" -c "Implemented (see git history); smoke/unit green. Closing as done. Product-level ship still gated by the Track A validation epic."
  done
fi

echo "== 4. Create epics (idempotent by title) =="
have_issue() { gh issue list -R "$REPO" --state all --limit 400 --json title --jq '.[].title' | grep -qxF "$1"; }
mk() { # title  labels  milestone  body
  if have_issue "$1"; then echo "   ok: $1";
  else run gh issue create -R "$REPO" --title "$1" --label "$2" --milestone "$3" --body "$4"; fi
}
GATE_NOTE="BLOCKED by the Track A validation gate. Captured for visibility only — do not start until 3/5 QA yeses. See docs/process/GITHUB_PM.md §0."

mk "EPIC · Track A Validation Gate (owner task)" "type:epic,priority:P0-critical,needs-human" "M0 · Ship Track A" \
"THE real finish line (HANDOVER §5). Show the tool to 5 QA professionals (spec→generate→pass on correct API→inject bug→tests catch→eject). 3/5 yes = Track A shipped.

Tasks:
- [ ] Recruit 5 QA (QA_OUTREACH_TEMPLATES.md)
- [ ] Run demo ×5 (QA_DEMO_KIT.md)
- [ ] Log verdicts + 'what would make you keep more?'
- [ ] Decision: 3/5 → unblock M1+; else iterate Track A.
Owner task — no agent can complete this."

mk "EPIC E7 · Reflector & Verdict Memory" "type:epic,priority:P1,area:divergence,blocked:validation-gate" "M2 · Reflector" \
"Net-new learning loop fed by healing/diagnose + divergence/witness. $GATE_NOTE
Tasks: E7-1 VerdictRecord+store · E7-2 reweight Skeptic · E7-3 Idioms · E7-4 wire into proof_run.
Exit: a rejected finding stops re-surfacing AND Skeptic hit-rate rises. See docs/vision/07_MASTER_PLAN.md."

mk "EPIC E8 · Perf Intelligence" "type:epic,priority:P2,area:perf,blocked:validation-gate,do-not-extend-until-gate" "M3 · Signals" \
"Scale up perf (quarantined k6/perf_analyzer) ON Track A: statistical→ML anomaly, generative load, LLM-aware metrics. $GATE_NOTE"

mk "EPIC E9 · Vision Perception" "type:epic,priority:P2,area:visual,blocked:validation-gate,do-not-extend-until-gate" "M3 · Signals" \
"VLM perception + semantic visual oracle + self-heal; reproduce D3 ui↔spec. Scales up visual_diff (quarantined). $GATE_NOTE"

mk "EPIC E10 · Explorer + Copilot v1" "type:epic,priority:P2,area:divergence,blocked:validation-gate" "M4 · Author & Trust" \
"Autonomous Explorer feeds Skeptic; NL-intent authoring for manual QA. $GATE_NOTE"

mk "EPIC E11 · Coverage SDET" "type:epic,priority:P2,area:artifact,blocked:validation-gate" "M4 · Author & Trust" \
"Unit-test emitter + bounded generate→run→repair loop; meaningful-assertion gate via self_play. $GATE_NOTE"

mk "EPIC E12 · Certification + Governance" "type:epic,priority:P2,area:substrate,blocked:validation-gate" "M4 · Author & Trust" \
"Model-certification gate (Gold-Set+RAG-Triad) on the router; governance KPIs; traceability; three-tier CI gates. $GATE_NOTE"

mk "EPIC E13 · Copilot v2 + Pairing" "type:epic,priority:P3,area:frontend,blocked:validation-gate" "M5 · Pairing & FE" \
"Mentor surfaces senior idioms to juniors; autonomy-ladder profiles. Depends on E7. $GATE_NOTE"

mk "EPIC FE · Dashboard Redesign" "type:epic,priority:P3,area:frontend,blocked:validation-gate,do-not-extend-until-gate" "M5 · Pairing & FE" \
"Redesign the (quarantined) dashboard per docs/dashboard/FE_REDESIGN.md (FE-0…FE-10). $GATE_NOTE
NOTE: track-b-c-deferred/ was re-integrated and deleted. Dashboard lives in the live tree."

echo
echo "Done. ${APPLY:+}$([ "$APPLY" = 1 ] && echo 'Applied.' || echo 'Dry-run only — re-run with --apply to mutate.')"
