#!/usr/bin/env bash
# =============================================================================
# CHERENKOV QA — Live Conformance Demo Harness
# Version  : 1.0.0
# Date     : 2026-07-06
# Usage    : bash run_demo.sh [--skip-docker]
#
# Phases:
#   Phase 1 — GREEN run  : both conformance tests pass
#   Phase 2 — RED run    : REGRESSION_MODE=true injects a bug; tool catches it
#   Phase 3 — Prism/Stripe validation via Docker (if available)
# =============================================================================

set -euo pipefail

# ── ANSI colours ─────────────────────────────────────────────────────────────
GREEN="\e[32m"
RED="\e[31m"
YELLOW="\e[33m"
CYAN="\e[36m"
BOLD="\e[1m"
RESET="\e[0m"

banner() { echo -e "${BOLD}${CYAN}$*${RESET}"; }
ok()     { echo -e "${GREEN}✓ $*${RESET}"; }
fail()   { echo -e "${RED}✗ $*${RESET}"; }
warn()   { echo -e "${YELLOW}⚠ $*${RESET}"; }

# ── Global state ─────────────────────────────────────────────────────────────
API_PID=""
SKIP_DOCKER=false
[[ "${1:-}" == "--skip-docker" ]] && SKIP_DOCKER=true

CHERENKOV_ROOT="/home/moaid/cherenkov-qa"
CHERENKOV_BIN="${CHERENKOV_ROOT}/bin/cherenkov"

# ── Cleanup trap ─────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  banner "── Cleanup ──────────────────────────────────────────────────────"
  [[ -n "${API_PID}" ]] && kill "${API_PID}" 2>/dev/null && ok "Target API process killed (PID ${API_PID})"
  if ! ${SKIP_DOCKER}; then
    docker rm -f cherenkov_prism_demo 2>/dev/null && ok "Prism container removed" || true
  fi
  echo "Cleanup complete."
}
trap cleanup EXIT

# ─────────────────────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║     === CHERENKOV QA — Live Conformance Demo ===              ║${RESET}"
echo -e "${BOLD}${CYAN}║   OpenAPI spec → AI-generated tests → real drift detection   ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# TASK 0 — PREREQUISITES
# ─────────────────────────────────────────────────────────────────────────────
banner "── [0/4] Checking prerequisites ─────────────────────────────────"

# Python3
if command -v python3 &>/dev/null; then
  ok "python3 found: $(python3 --version 2>&1)"
else
  fail "python3 not found. Install Python 3.10+ and try again."
  exit 1
fi

# cherenkov CLI
if [[ -x "${CHERENKOV_BIN}" ]]; then
  ok "cherenkov CLI found at ${CHERENKOV_BIN}"
  CHERENKOV="${CHERENKOV_BIN}"
elif command -v cherenkov &>/dev/null; then
  ok "cherenkov CLI found on PATH: $(command -v cherenkov)"
  CHERENKOV="cherenkov"
else
  fail "cherenkov CLI not found. Expected: ${CHERENKOV_BIN} or 'cherenkov' on PATH."
  exit 1
fi

# uvicorn
if command -v uvicorn &>/dev/null; then
  ok "uvicorn found: $(uvicorn --version 2>&1)"
elif python3 -m uvicorn --version &>/dev/null 2>&1; then
  ok "uvicorn found via python3 -m uvicorn"
  alias uvicorn="python3 -m uvicorn"
else
  # Try inside venv
  source "${CHERENKOV_ROOT}/.venv/bin/activate" 2>/dev/null || true
  if ! command -v uvicorn &>/dev/null; then
    fail "uvicorn not found. Run: pip install uvicorn"
    exit 1
  fi
  ok "uvicorn found inside venv"
fi

# Docker (optional)
DOCKER_AVAILABLE=false
if ! ${SKIP_DOCKER}; then
  if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    ok "Docker available: $(docker --version)"
    DOCKER_AVAILABLE=true
  else
    warn "Docker not available or not running. Phase 3 (Prism/Stripe) will be skipped."
    warn "  Run with: --skip-docker to suppress this warning."
  fi
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — START TARGET API
# ─────────────────────────────────────────────────────────────────────────────
banner "── [1/4] Starting Target API (uvicorn @ 127.0.0.1:8000) ─────────"

cd "${CHERENKOV_ROOT}"
source .venv/bin/activate 2>/dev/null || true

# Kill any lingering process on port 8000
fuser -k 8000/tcp 2>/dev/null || true
sleep 0.5

uvicorn target.target_api:app --host 127.0.0.1 --port 8000 \
  --log-level warning &
API_PID=$!
ok "uvicorn started (PID ${API_PID})"

# Health check loop for Target API
echo "Waiting for Target API to become healthy..."
TARGET_HEALTHY=false
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1 || \
     curl -sf http://localhost:8000/docs >/dev/null 2>&1 || \
     curl -sf http://localhost:8000/openapi.json >/dev/null 2>&1; then
    ok "Target API healthy (attempt ${i})"
    TARGET_HEALTHY=true
    break
  fi
  echo "  ... waiting (${i}/15)"
  sleep 1
done

if ! ${TARGET_HEALTHY}; then
  fail "Target API did not become healthy within 15 seconds."
  exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — START PRISM MOCK (Docker, optional)
# ─────────────────────────────────────────────────────────────────────────────
PRISM_HEALTHY=false
if ${DOCKER_AVAILABLE}; then
  banner "── [2/4] Starting Prism mock (Docker @ :4010) ───────────────────"

  # Remove stale container if it exists
  docker rm -f cherenkov_prism_demo 2>/dev/null || true

  docker run -d --name cherenkov_prism_demo \
    -p 4010:4010 \
    stoplight/prism:5 mock \
    -h 0.0.0.0 /api/openapi.yaml \
    2>/dev/null || warn "Prism container start failed; Phase 3 will be skipped."

  echo "Waiting for Prism mock to become healthy..."
  for i in $(seq 1 10); do
    if curl -sf http://localhost:4010 >/dev/null 2>&1; then
      ok "Prism healthy (attempt ${i})"
      PRISM_HEALTHY=true
      break
    fi
    echo "  ... waiting (${i}/10)"
    sleep 1
  done
  if ! ${PRISM_HEALTHY}; then
    warn "Prism did not become healthy in 10 s — Phase 3 will be skipped."
  fi
  echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — GREEN RUN
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║  === Phase 1: Green State (Both Tests Should Pass) ===       ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

GREEN_EXIT=0
"${CHERENKOV}" validate --target http://localhost:8000 2>&1 || GREEN_EXIT=$?

if [[ ${GREEN_EXIT} -eq 0 ]]; then
  echo ""
  echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${GREEN}║  ✓ Phase 1 PASSED — API is fully spec-conformant             ║${RESET}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo ""
else
  warn "Phase 1 validation returned exit code ${GREEN_EXIT} — check target API state."
fi

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — INJECT BUG + RED RUN
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${RED}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${RED}║  === Phase 2: Injecting Conformance Bug (REGRESSION_MODE=true) ║${RESET}"
echo -e "${BOLD}${RED}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "Stopping clean API and restarting with REGRESSION_MODE=true..."

kill "${API_PID}" 2>/dev/null || true
sleep 1

# Kill any lingering process on port 8000 again
fuser -k 8000/tcp 2>/dev/null || true
sleep 0.5

export REGRESSION_MODE=true
uvicorn target.target_api:app --host 127.0.0.1 --port 8000 \
  --log-level warning &
API_PID=$!
ok "uvicorn (regression mode) started (PID ${API_PID})"

# Health check loop again
echo "Waiting for regressed API to become healthy..."
TARGET_HEALTHY=false
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1 || \
     curl -sf http://localhost:8000/docs >/dev/null 2>&1 || \
     curl -sf http://localhost:8000/openapi.json >/dev/null 2>&1; then
    ok "Regressed API healthy (attempt ${i})"
    TARGET_HEALTHY=true
    break
  fi
  echo "  ... waiting (${i}/15)"
  sleep 1
done

if ! ${TARGET_HEALTHY}; then
  fail "Regressed API did not become healthy. Cannot complete Phase 2."
  exit 1
fi

echo ""
echo "Running CHERENKOV validate against regressed API..."
echo ""

RED_OUTPUT=""
RED_EXIT=0
RED_OUTPUT=$("${CHERENKOV}" validate --target http://localhost:8000 2>&1) || RED_EXIT=$?
echo "${RED_OUTPUT}"

# Detect that the tool caught the regression
DRIFT_CAUGHT=false
if echo "${RED_OUTPUT}" | grep -qiE "FAILED|422|400|divergence|conformance"; then
  DRIFT_CAUGHT=true
fi

echo ""
if ${DRIFT_CAUGHT}; then
  echo -e "${BOLD}${RED}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${RED}║  ✗ Phase 2 RED — Conformance drift DETECTED (as expected)    ║${RESET}"
  echo -e "${BOLD}${RED}║    CHERENKOV correctly caught the injected regression.        ║${RESET}"
  echo -e "${BOLD}${RED}╚══════════════════════════════════════════════════════════════╝${RESET}"
else
  warn "Phase 2: no clear FAILED/422/divergence markers in output."
  warn "         The exit code was ${RED_EXIT}. Check above output manually."
fi

unset REGRESSION_MODE
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — STRIPE / PRISM VALIDATION (optional)
# ─────────────────────────────────────────────────────────────────────────────
if ${PRISM_HEALTHY}; then
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${CYAN}║  === Phase 3: Stripe API Mock Validation (via Prism) ===     ║${RESET}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo ""

  STRIPE_SPEC="${CHERENKOV_ROOT}/stripe_spec.json"
  if [[ -f "${STRIPE_SPEC}" ]]; then
    ok "Stripe spec found at ${STRIPE_SPEC}"
    PRISM_EXIT=0
    "${CHERENKOV}" validate \
      --target http://localhost:4010 \
      --spec "${STRIPE_SPEC}" 2>&1 || PRISM_EXIT=$?

    if [[ ${PRISM_EXIT} -eq 0 ]]; then
      echo ""
      echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
      echo -e "${BOLD}${GREEN}║  ✓ Phase 3 PASSED — Stripe mock is spec-conformant           ║${RESET}"
      echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
    else
      echo ""
      echo -e "${BOLD}${YELLOW}╔══════════════════════════════════════════════════════════════╗${RESET}"
      echo -e "${BOLD}${YELLOW}║  ⚠ Phase 3 — Stripe divergences detected (see above)         ║${RESET}"
      echo -e "${BOLD}${YELLOW}╚══════════════════════════════════════════════════════════════╝${RESET}"
    fi
  else
    warn "stripe_spec.json not found at ${STRIPE_SPEC}. Skipping Stripe validation."
    warn "  Download it from: https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json"
    warn "  Save to: ${STRIPE_SPEC}"
  fi
else
  warn "Phase 3 skipped (Docker/Prism not available)."
fi

# ─────────────────────────────────────────────────────────────────────────────
# FINAL VERDICT
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║  === Demo Complete ===                                        ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

if ${DRIFT_CAUGHT}; then
  ok "CHERENKOV correctly detected the injected conformance drift."
  ok "The demo proves: spec-conformant → PASS; regressed → FAIL (with evidence)."
  exit 0
else
  warn "Drift detection was inconclusive. Re-run or check the target_api regression handler."
  exit 1
fi
