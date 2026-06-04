#!/usr/bin/env bash
# scripts/run_smoke_matrix.sh — run full local smoke matrix
# Usage: bash scripts/run_smoke_matrix.sh
set -euo pipefail
cd "$(dirname "$0")/.."

TESTS=(
  smoke_test_healing.py
  smoke_test_polish.py
  smoke_test_certification.py
  smoke_test_governance.py
  smoke_test_validate_gate.py
  smoke_test_e7_behavioral.py
  smoke_test_hitl_cli.py
  smoke_test_reflector_cli.py
  smoke_test_reflector_suppression.py
  smoke_test_mentor.py
  smoke_test_autonomy.py
  smoke_test_vision_e9.py
  smoke_test_openclaw.py
  smoke_test_perf_anomaly.py
  smoke_test_emitters_unit.py
)

pass=0
fail=0
echo "=== Full smoke matrix ==="
for f in "${TESTS[@]}"; do
  if PYTHONPATH=. python3 "$f" > /tmp/smoke_out.txt 2>&1; then
    echo "[PASS] $f"
    pass=$((pass+1))
  else
    echo "[FAIL] $f"
    tail -5 /tmp/smoke_out.txt
    fail=$((fail+1))
  fi
done

echo ""
echo "==================================="
echo "  Matrix: $pass pass, $fail fail"
echo "==================================="
exit $fail
