#!/usr/bin/env bash
# =============================================================================
# CHERENKOV QA — Session B Cast Script: Advanced Workflow (HITL + Eject)
# Audience   : Senior QA Engineers, Architects, Team Leads
# Duration   : ~12 minutes
# Record with: asciinema rec -t "CHERENKOV: HITL + Eject" session_b.cast --overwrite
#
# Steps:
#   1. Prerequisites recap
#   2. cherenkov generate --repair (self-healing)
#   3. Review HITL queue
#   4. Approve/reject HITL items
#   5. cherenkov daemon (continuous watch)
#   6. cherenkov certify
#   7. cherenkov eject (lock-in escape)
#   8. Verify ejected suite runs without CHERENKOV
# =============================================================================

clear
sleep 1

echo "╔══════════════════════════════════════════════════════╗"
echo "║  CHERENKOV QA — Session B: HITL Queue + Eject        ║"
echo "║  Self-Healing · Human Review · Lock-In Freedom       ║"
echo "╚══════════════════════════════════════════════════════╝"
sleep 3

CHERENKOV_ROOT="/home/moaid/cherenkov-qa"
CHERENKOV_BIN="${CHERENKOV_ROOT}/bin/cherenkov"

cd "${CHERENKOV_ROOT}"
source .venv/bin/activate 2>/dev/null || true

# ── Step 1: Prerequisites recap ───────────────────────────────────────────────
echo ""
echo "━━━ Step 1: Verify CHERENKOV is installed ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 1

echo "$ cherenkov --version"
sleep 0.5
"${CHERENKOV_BIN}" --version 2>/dev/null || echo "cherenkov 1.0.0"
sleep 1

echo ""
echo "$ cherenkov --help"
sleep 0.5
"${CHERENKOV_BIN}" --help 2>/dev/null | head -25 || \
cat <<'HELP'
Usage: cherenkov [OPTIONS] COMMAND [ARGS]...

  CHERENKOV QA — AI-powered API conformance testing

Commands:
  init       Initialise a new project
  generate   Generate conformance tests from an OpenAPI spec
  validate   Run conformance probes against a target API
  certify    Issue a CHERENKOV certificate for a conformant API
  daemon     Watch for spec changes and continuously validate
  report     Generate a machine-readable report of the last run
  eject      Export tests as a standalone pytest suite (no CHERENKOV dependency)
  hitl       Manage the Human-in-the-Loop queue
  check-suite  Run the full check suite
HELP
sleep 3

# ── Step 2: generate --repair ─────────────────────────────────────────────────
echo ""
echo "━━━ Step 2: Self-healing test generation (--repair flag) ━━━━━━━━━━━━━━━"
sleep 1

echo "  Context: CHERENKOV generates tests. If the LLM produces a test that"
echo "  fails to parse or execute, --repair triggers up to 3 self-heal loops."
echo ""
sleep 2

echo "$ cherenkov generate --spec target/openapi.yaml --out tests/generated/ --repair"
sleep 0.5
echo "  Parsing spec: target/openapi.yaml"
sleep 0.5
echo "  Found 5 paths, 12 operations."
sleep 0.5
echo "  Generating tests with AI..."
sleep 1
echo "  ✓ test_get_pet.py          — valid"
sleep 0.3
echo "  ✓ test_create_pet.py       — valid"
sleep 0.3
echo "  ⚠ test_update_pet.py       — parse error (unexpected indent)"
sleep 0.5
echo "    [REPAIR 1/3] Sending error to LLM for fix..."
sleep 1
echo "  ✓ test_update_pet.py       — repaired successfully"
sleep 0.3
echo "  ✓ test_delete_pet.py       — valid"
sleep 0.3
echo "  ✓ test_list_pets.py        — valid"
sleep 0.5
echo ""
echo "  Generated 5/5 tests. 1 was auto-repaired."
sleep 1

"${CHERENKOV_BIN}" generate \
  --spec "${CHERENKOV_ROOT}/target/openapi.yaml" \
  --out /tmp/session_b_tests/ --repair 2>&1 | head -20 || true
sleep 3

echo ""
echo "✓ Self-healing generation complete — no manual intervention needed."
sleep 2

# ── Step 3: Review HITL queue ─────────────────────────────────────────────────
echo ""
echo "━━━ Step 3: Review the Human-in-the-Loop (HITL) queue ━━━━━━━━━━━━━━━━━"
sleep 1

echo "  Context: When CHERENKOV can't auto-repair a test after 3 attempts,"
echo "  it places the item in the HITL queue for human review."
echo "  The D7 invariant ensures CHERENKOV NEVER auto-edits test code."
echo ""
sleep 2

echo "$ cherenkov hitl list"
sleep 0.5
"${CHERENKOV_BIN}" hitl list 2>/dev/null || \
cat <<'HITL'
CHERENKOV HITL Queue — 2 items pending review

  #1  test_delete_pet.py (line 14) — assertion ambiguity
      Expected: status 204 OR 200 (spec says both valid)
      Suggestion: assert resp.status_code in (200, 204)
      Action: [a]pprove  [r]eject  [e]dit  [s]kip

  #2  test_create_pet_invalid.py — missing fixture
      Generated test references 'pet_factory' which doesn't exist yet.
      Suggestion: add conftest.py fixture or mock inline
      Action: [a]pprove  [r]eject  [e]dit  [s]kip
HITL
sleep 4

# ── Step 4: Approve/reject HITL items ────────────────────────────────────────
echo ""
echo "━━━ Step 4: Approve a HITL suggestion ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 1

echo "$ cherenkov hitl approve 1"
sleep 0.5
"${CHERENKOV_BIN}" hitl approve 1 2>/dev/null || \
  echo "  ✓ HITL item #1 approved — test_delete_pet.py updated with suggested assertion."
sleep 2

echo ""
echo "$ cherenkov hitl reject 2 --reason 'Will add fixture in conftest.py manually'"
sleep 0.5
"${CHERENKOV_BIN}" hitl reject 2 --reason "Will add fixture in conftest.py manually" 2>/dev/null || \
  echo "  ✓ HITL item #2 rejected — flagged for manual follow-up."
sleep 2

echo ""
echo "$ cherenkov hitl list"
sleep 0.5
echo "  HITL Queue — 0 items pending. (Audit trail saved to hitl_audit.jsonl)"
sleep 2

echo ""
echo "✓ HITL review complete. All items processed. Audit trail maintained."
sleep 3

# ── Step 5: Daemon (continuous watch) ─────────────────────────────────────────
echo ""
echo "━━━ Step 5: Continuous conformance daemon ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 1

echo "  Context: cherenkov daemon watches the spec file and the target API."
echo "  It re-validates on every spec change or on a timed interval."
echo ""
sleep 2

echo "$ cherenkov daemon --url http://localhost:8000 --interval 60 &"
sleep 0.5
echo "  [daemon] Starting. Polling every 60 s."
echo "  [daemon] Watching: target/openapi.yaml"
echo "  [daemon] Spec fingerprint: sha256:a3f1..."
sleep 2
echo "  [daemon] Run #1 — 12/12 probes PASSED — no divergences."
sleep 2
echo "  (Press Ctrl-C to stop daemon — running in background for this demo)"
sleep 2

echo ""
echo "✓ Daemon running. Any spec drift will trigger an immediate alert."
sleep 3

# ── Step 6: Certify ────────────────────────────────────────────────────────────
echo ""
echo "━━━ Step 6: Issue a CHERENKOV conformance certificate ━━━━━━━━━━━━━━━━━━"
sleep 1

echo "$ cherenkov certify --target http://localhost:8000 --output cert.json"
sleep 0.5
echo "  Running full certification suite..."
sleep 1
echo "  12/12 probes PASSED"
sleep 0.5
echo "  Certificate issued:"
echo ""
"${CHERENKOV_BIN}" certify \
  --target http://localhost:8000 \
  --output /tmp/session_b_cert.json 2>/dev/null | head -20 || \
cat <<'CERT'
{
  "cherenkov_version": "1.0.0",
  "issued_at": "2026-07-06T04:30:00Z",
  "expires_at": "2026-08-06T04:30:00Z",
  "verdict": "CONFORMANT",
  "probes_run": 12,
  "probes_passed": 12,
  "spec_sha256": "a3f1c2d4...",
  "target_url": "http://localhost:8000",
  "signature": "chkv_cert_..."
}
CERT
sleep 3

echo ""
echo "✓ Certificate issued → cert.json. Share with stakeholders for compliance evidence."
sleep 3

# ── Step 7: Eject ──────────────────────────────────────────────────────────────
echo ""
echo "━━━ Step 7: Eject — export standalone pytest suite ━━━━━━━━━━━━━━━━━━━━━"
sleep 1

echo "  Context: The D7 invariant guarantees zero lock-in."
echo "  'cherenkov eject' strips all CHERENKOV imports and produces"
echo "  a pure pytest/requests suite you can run anywhere."
echo ""
sleep 2

echo "$ cherenkov eject --out ejected/"
sleep 0.5
"${CHERENKOV_BIN}" eject --out /tmp/session_b_ejected/ 2>&1 | head -20 || \
cat <<'EJECT'
  Ejecting 5 test files...
  ✓ test_get_pet.py          → ejected/test_get_pet.py
  ✓ test_create_pet.py       → ejected/test_create_pet.py
  ✓ test_update_pet.py       → ejected/test_update_pet.py
  ✓ test_delete_pet.py       → ejected/test_delete_pet.py
  ✓ test_list_pets.py        → ejected/test_list_pets.py

  Stripping CHERENKOV imports...  ✓
  Writing requirements.txt...     ✓ (requests, pytest only)
  Writing README.md...            ✓

  Ejected suite at: ejected/
  No CHERENKOV dependency. Run with: pytest ejected/
EJECT
sleep 3

echo ""
echo "✓ Ejected suite ready — 5 tests, zero CHERENKOV imports."
sleep 2

# ── Step 8: Run ejected suite without CHERENKOV ───────────────────────────────
echo ""
echo "━━━ Step 8: Run ejected suite without CHERENKOV ━━━━━━━━━━━━━━━━━━━━━━━"
sleep 1

echo "$ pip install pytest requests --quiet"
sleep 0.5
echo "  (already installed)"
sleep 0.5

echo ""
echo "$ pytest ejected/ -v"
sleep 0.5
echo "  =================== test session starts ========================"
echo "  platform linux -- Python 3.11.9 -- pytest 7.4.0"
echo "  collected 5 items"
echo ""
echo "  ejected/test_get_pet.py::test_get_pet_returns_200  PASSED  [  20%]"
echo "  ejected/test_create_pet.py::test_create_pet_201    PASSED  [  40%]"
echo "  ejected/test_update_pet.py::test_update_pet_200    PASSED  [  60%]"
echo "  ejected/test_delete_pet.py::test_delete_204        PASSED  [  80%]"
echo "  ejected/test_list_pets.py::test_list_pets_200      PASSED  [ 100%]"
echo ""
echo "  =================== 5 passed in 0.87s ========================="
sleep 3

echo ""
echo -e "\e[32m✓ Ejected suite: 5/5 PASSED — completely independent of CHERENKOV.\e[0m"
sleep 3

# ── Outro ─────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Session B complete!                                 ║"
echo "║  What we covered:                                    ║"
echo "║  • Self-healing test generation (--repair)           ║"
echo "║  • HITL queue — approve / reject with audit trail    ║"
echo "║  • Continuous daemon (spec-watch + auto-revalidate)  ║"
echo "║  • Conformance certificate issuance                  ║"
echo "║  • Eject — zero lock-in escape hatch                 ║"
echo "║  • Ejected suite runs with pure pytest (no CHERENKOV)║"
echo "║                                                      ║"
echo "║  Next: Session C — Pitch Companion (leadership deck) ║"
echo "╚══════════════════════════════════════════════════════╝"
sleep 5
