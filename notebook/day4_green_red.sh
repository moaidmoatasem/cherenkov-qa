#!/usr/bin/env bash
# CHERENKOV Week 0 — Day 4: the green->red proof
# The entire validation hinges on this transition, so this script is written to
# FAIL LOUDLY rather than emit a false verdict. It verifies the server is up and
# that the bug toggle actually flipped before trusting any test run.
#
# Prereq: generated tests exist (Day 1) and reference the openapi-fetch client;
#         playwright.config.ts baseURL points at http://localhost:8000.

set -uo pipefail   # NOT -e: we manage exit codes explicitly so the verdict always prints

PORT=8000
BASE="http://localhost:${PORT}"
TARGET_DIR="../target"
PIDFILE="/tmp/cherenkov_target.pid"

# --- helpers -------------------------------------------------------------

free_port() {
  # kill anything already bound to the port (stale server from a previous run)
  local pids
  pids="$(lsof -ti tcp:${PORT} 2>/dev/null || true)"
  if [ -n "${pids}" ]; then
    echo "    freeing port ${PORT} (killing: ${pids})"
    kill -9 ${pids} 2>/dev/null || true
    sleep 1
  fi
}

start_server() {
  # $1 = "off" | "on"   -> sets REGRESSION_MODE accordingly
  local mode_env=""
  if [ "$1" = "on" ]; then
    export REGRESSION_MODE=true
  else
    export REGRESSION_MODE=false
  fi
  free_port
  ( cd "${TARGET_DIR}" && .venv/bin/uvicorn target_api:app --port ${PORT} \
      >"/tmp/cherenkov_target_$1.log" 2>&1 & echo $! > "${PIDFILE}" )
}

wait_until_healthy() {
  # poll /health until it answers (max ~20s) instead of a blind sleep
  local i
  for i in $(seq 1 40); do
    if curl -sf "${BASE}/health" >/dev/null 2>&1; then return 0; fi
    sleep 0.5
  done
  echo "    ERROR: server never became healthy. See /tmp/cherenkov_target_*.log"
  return 1
}

assert_mode() {
  # $1 = expected "true" | "false" — proves the toggle actually flipped
  local actual
  actual="$(curl -sf "${BASE}/health" | grep -o '"regression_mode":[^,}]*' | grep -o '[^:]*$' | tr -d ' ')"
  if [ "${actual}" != "$1" ]; then
    echo "    ERROR: expected regression_mode=$1 but server reports ${actual}."
    echo "    The bug toggle did not take effect — verdict would be meaningless."
    return 1
  fi
  echo "    confirmed regression_mode=${actual}"
}

stop_server() {
  if [ -f "${PIDFILE}" ]; then
    kill -9 "$(cat "${PIDFILE}")" 2>/dev/null || true
  fi
  rm -f "${PIDFILE}"
  free_port
  sleep 1
}

run_suite() {
  # Run Playwright tests from the stub directory
  ( cd ../stub && npx playwright test >/tmp/playwright_run.log 2>&1 )
  local exit_code=$?
  if [ $exit_code -ne 0 ]; then
    echo "    Playwright failed. Log preview (last 10 lines):"
    tail -n 10 /tmp/playwright_run.log
  fi
  return $exit_code
}

# --- pre-flight ----------------------------------------------------------

echo "=== Day 4: green -> red bug-catch proof ==="
for cmd in curl npx lsof; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "MISSING: $cmd is required."; exit 2; }
done
GREEN_EXIT=99; RED_EXIT=99
trap stop_server EXIT   # always clean up the server, however we exit

# --- pass 1: bug OFF, expect GREEN --------------------------------------

echo
echo "[1/4] Starting Target API — bug OFF..."
start_server off
wait_until_healthy || exit 1
assert_mode "false" || exit 1

echo "[2/4] Running suite against CORRECT API — expect GREEN..."
run_suite; GREEN_EXIT=$?
echo "    suite exit=${GREEN_EXIT}"
stop_server

# --- pass 2: bug ON, expect RED -----------------------------------------

echo
echo "[3/4] Starting Target API — bug ON (REGRESSION_MODE=true)..."
start_server on
wait_until_healthy || exit 1
assert_mode "true" || exit 1

echo "[4/4] Running suite against BUGGY API — expect RED..."
run_suite; RED_EXIT=$?
echo "    suite exit=${RED_EXIT}"
stop_server

# --- verdict -------------------------------------------------------------

echo
echo "================ RESULT ================"
if [ "${GREEN_EXIT}" -eq 0 ] && [ "${RED_EXIT}" -ne 0 ]; then
  echo "  PASS: GREEN with bug off, RED with bug on."
  echo "  The tests catch the regression. This is the Week 0 signal."
  VERDICT=0
elif [ "${GREEN_EXIT}" -ne 0 ]; then
  echo "  INCONCLUSIVE: suite was not green on the CORRECT API."
  echo "    bug OFF exit=${GREEN_EXIT} (want 0)."
  echo "    Tests fail even when the API is right — fix the tests/config first,"
  echo "    this is not a real bug-catch signal yet."
  VERDICT=1
else
  echo "  FAIL: tests stayed GREEN even with the bug ON."
  echo "    bug ON exit=${RED_EXIT} (want non-zero)."
  echo "    The assertions are too shallow to catch the regression. Inspect them."
  VERDICT=1
fi
echo "========================================"
exit ${VERDICT}
