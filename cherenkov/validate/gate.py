"""
cherenkov/validate/gate.py
ValidationGate – runs Track-A smoke scripts and returns a ValidationReport.
"""

from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cherenkov.validate.contracts import (
    GateCriteria,
    GateEvidence,
    ValidationReport,
)
from cherenkov.validate.evidence import EvidenceCollector


class ValidationGate:
    """Execute all gate checks and produce a signed ValidationReport.

    Gate criteria
    -------------
    Each entry specifies a smoke script and whether it is *required* for a
    'pass' result.  Optional failures produce 'degraded'; required failures
    produce 'fail'.
    """

    GATE_CRITERIA: list[GateCriteria] = [
        GateCriteria(
            name="smoke_track_a",
            description="Core Track-A API conformance smoke (smoke_test.py) passes",
            required=True,
        ),
        GateCriteria(
            name="smoke_hitl_race",
            description="HITL race-condition smoke (smoke_test_hitl_race.py) passes",
            required=True,
        ),
        GateCriteria(
            name="smoke_hitl_concurrency",
            description="HITL concurrency smoke (smoke_test_hitl_concurrency.py) passes",
            required=True,
        ),
        GateCriteria(
            name="smoke_hitl_cli",
            description="HITL CLI smoke (smoke_test_hitl_cli.py) passes",
            required=True,
        ),
        GateCriteria(
            name="smoke_eject",
            description="Eject anti-lock-in smoke (smoke_test_eject.py) passes",
            required=True,
        ),
        GateCriteria(
            name="smoke_validate",
            description="Validate-gate smoke (smoke_test_validate.py) passes",
            required=True,
        ),
        GateCriteria(
            name="smoke_healing",
            description="Healing suggest-only smoke (smoke_test_healing.py) passes",
            required=False,
        ),
        GateCriteria(
            name="smoke_polish",
            description="Polish smoke (smoke_test_polish.py) passes",
            required=False,
        ),
    ]

    # Map gate name → smoke script filename
    _GATE_SCRIPTS: dict[str, str] = {
        "smoke_track_a": "smoke_test.py",
        "smoke_hitl_race": "smoke_test_hitl_race.py",
        "smoke_hitl_concurrency": "smoke_test_hitl_concurrency.py",
        "smoke_hitl_cli": "smoke_test_hitl_cli.py",
        "smoke_eject": "smoke_test_eject.py",
        "smoke_validate": "smoke_test_validate.py",
        "smoke_healing": "smoke_test_healing.py",
        "smoke_polish": "smoke_test_polish.py",
    }

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        run_id: str | None = None,
        evidence_dir: str | None = None,
        _subprocess_runner: Any | None = None,
    ) -> ValidationReport:
        """Run all gate checks and return a ValidationReport.

        Parameters
        ----------
        run_id:
            Unique identifier for this run.  Auto-generated when *None*.
        evidence_dir:
            Directory path for captured output files.  Skipped when *None*.
        _subprocess_runner:
            Injection point for tests – a callable with the same signature as
            ``subprocess.run``.  When *None*, the real ``subprocess.run`` is used.
        """
        run_id = run_id or str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        collector: EvidenceCollector | None = None
        if evidence_dir:
            collector = EvidenceCollector(base_dir=evidence_dir)

        runner = _subprocess_runner or subprocess.run

        gate_results: list[GateEvidence] = []
        for criteria in self.GATE_CRITERIA:
            evidence = self._run_one_gate(criteria, runner, collector)
            gate_results.append(evidence)

        result = self._compute_result(gate_results)
        summary = self._build_summary(gate_results, result)

        return ValidationReport(
            run_id=run_id,
            timestamp=timestamp,
            result=result,  # type: ignore
            gates=gate_results,
            summary=summary,
            evidence_dir=evidence_dir,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_one_gate(
        self,
        criteria: GateCriteria,
        runner: Any,
        collector: EvidenceCollector | None,
    ) -> GateEvidence:
        script = self._GATE_SCRIPTS[criteria.name]
        script_path = self.project_root / script

        try:
            proc = runner(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )
            passed = proc.returncode == 0
            combined = (proc.stdout or "") + (proc.stderr or "")
            detail = f"exit={proc.returncode}"
        except FileNotFoundError:
            passed = False
            combined = f"Script not found: {script_path}"
            detail = "script_not_found"
        except Exception as exc:  # noqa: BLE001
            passed = False
            combined = str(exc)
            detail = f"exception: {type(exc).__name__}"

        evidence_ref: str | None = None
        if collector:
            evidence_ref = collector.record(
                name=criteria.name,
                passed=passed,
                output=combined,
                detail=detail,
            )

        return GateEvidence(
            gate=criteria.name,
            passed=passed,
            detail=detail,
            evidence_ref=evidence_ref,
        )

    @staticmethod
    def _compute_result(gates: list[GateEvidence]) -> str:
        """Determine overall result based on gate outcomes and criteria."""
        # Build name→required mapping from GATE_CRITERIA
        required_map: dict[str, bool] = {
            c.name: c.required for c in ValidationGate.GATE_CRITERIA
        }

        any_required_fail = False
        any_optional_fail = False

        for gate in gates:
            if gate.passed:
                continue
            if required_map.get(gate.gate, True):
                any_required_fail = True
            else:
                any_optional_fail = True

        if any_required_fail:
            return "fail"
        if any_optional_fail:
            return "degraded"
        return "pass"

    @staticmethod
    def _build_summary(gates: list[GateEvidence], result: str) -> str:
        total = len(gates)
        passed = sum(1 for g in gates if g.passed)
        failed_names = [g.gate for g in gates if not g.passed]
        summary = f"result={result.upper()}  gates={passed}/{total} passed"
        if failed_names:
            summary += f"  failed=[{', '.join(failed_names)}]"
        return summary
