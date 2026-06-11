"""
smoke_test_validate_gate.py
Kill-criterion exit demo for the Validation Gate (A4 #112).

Uses a mocked subprocess runner so it runs without Prism/Docker.
Exit 0 = kill criterion met.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

from cherenkov.validate import ValidationGate, ValidationReport


def _mock_runner_all_pass(*args, **kwargs):
    """Simulate all smoke scripts passing."""
    return SimpleNamespace(returncode=0, stdout="[PASS] mocked smoke\n", stderr="")


def _verify_report(report: ValidationReport, label: str) -> bool:
    ok = True

    # 1. schema_version must be 'validate/v1'
    if report.schema_version != "validate/v1":
        print(f"  [FAIL] {label}: schema_version={report.schema_version!r} (expected 'validate/v1')")
        ok = False
    else:
        print(f"  [PASS] {label}: schema_version={report.schema_version!r}")

    # 2. result must be one of pass/fail/degraded
    if report.result not in ("pass", "fail", "degraded"):
        print(f"  [FAIL] {label}: result={report.result!r} not in {{pass, fail, degraded}}")
        ok = False
    else:
        print(f"  [PASS] {label}: result={report.result!r}")

    # 3. gates list must be non-empty
    if not report.gates:
        print(f"  [FAIL] {label}: gates list is empty")
        ok = False
    else:
        print(f"  [PASS] {label}: {len(report.gates)} gate entries present")

    # 4. Pydantic round-trip
    try:
        data = report.model_dump()
        restored = ValidationReport.model_validate(data)
        if restored.schema_version != "validate/v1":
            raise ValueError("schema_version mismatch after round-trip")
        print(f"  [PASS] {label}: Pydantic round-trip OK")
    except Exception as exc:
        print(f"  [FAIL] {label}: Pydantic round-trip failed: {exc}")
        ok = False

    return ok


def main() -> int:
    print("=" * 60)
    print("smoke_test_validate_gate.py — Validation Gate kill-criterion demo")
    print("=" * 60)

    gate = ValidationGate()
    all_ok = True

    # --- Scenario 1: all gates pass → result='pass' ---
    print("\nScenario 1: all gates pass (mocked)")
    report1 = gate.run(run_id="smoke-1", _subprocess_runner=_mock_runner_all_pass)
    print(f"  Summary: {report1.summary}")
    ok1 = _verify_report(report1, "all-pass")
    if report1.result != "pass":
        print(f"  [FAIL] expected result='pass', got {report1.result!r}")
        ok1 = False
    else:
        print(f"  [PASS] result='pass' confirmed")
    all_ok = all_ok and ok1

    # --- Scenario 2: one required gate fails → result='fail' ---
    print("\nScenario 2: one required gate fails (mocked)")
    call_count = [0]

    def _mock_runner_first_fail(*args, **kwargs):
        call_count[0] += 1
        rc = 1 if call_count[0] == 1 else 0
        return SimpleNamespace(returncode=rc, stdout="", stderr="simulated failure" if rc else "ok")

    report2 = gate.run(run_id="smoke-2", _subprocess_runner=_mock_runner_first_fail)
    print(f"  Summary: {report2.summary}")
    ok2 = _verify_report(report2, "required-fail")
    if report2.result != "fail":
        print(f"  [FAIL] expected result='fail', got {report2.result!r}")
        ok2 = False
    else:
        print(f"  [PASS] result='fail' confirmed")
    all_ok = all_ok and ok2

    # --- Scenario 3: one optional gate fails → result='degraded' ---
    print("\nScenario 3: last optional gate fails (mocked smoke_polish)")
    call_count2 = [0]
    num_gates = len(ValidationGate.GATE_CRITERIA)

    def _mock_runner_last_optional_fail(*args, **kwargs):
        call_count2[0] += 1
        rc = 1 if call_count2[0] == num_gates else 0
        return SimpleNamespace(returncode=rc, stdout="", stderr="")

    report3 = gate.run(run_id="smoke-3", _subprocess_runner=_mock_runner_last_optional_fail)
    print(f"  Summary: {report3.summary}")
    ok3 = _verify_report(report3, "optional-fail")
    if report3.result != "degraded":
        print(f"  [FAIL] expected result='degraded', got {report3.result!r}")
        ok3 = False
    else:
        print(f"  [PASS] result='degraded' confirmed")
    all_ok = all_ok and ok3

    # --- Final verdict ---
    print("\n" + "=" * 60)
    if all_ok:
        print("[PASS] smoke_test_validate_gate: kill criterion MET — exit 0")
        return 0
    else:
        print("[FAIL] smoke_test_validate_gate: kill criterion NOT MET — exit 1")
        return 1


if __name__ == "__main__":
    sys.exit(main())
