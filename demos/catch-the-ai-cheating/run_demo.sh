#!/usr/bin/env bash
# Catch the AI cheating — G0 / E0.2 demo. Shows the control passing and each
# cheat being caught. Exit 0 only if the control is clean AND all 3 cheats are caught.
set -u
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
run() { "$PY" integrity_check.py --spec openapi.yaml --baseline suite_good.py "$@"; }

fail=0
echo "### 1. Honest control (expect PASS)"
run --candidate suite_good.py --label "good (control)" || fail=1

for c in weakened deleted hallucinated; do
  echo
  echo "### cheat: $c (expect CAUGHT)"
  if run --candidate "suite_cheat_${c}.py"; then
    echo "!! NOT CAUGHT — demo FAILED"
    fail=1
  else
    echo ">> caught as expected"
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "DEMO PASS: honest suite clean, all 3 cheats caught."
else
  echo "DEMO FAIL"
fi
exit "$fail"
