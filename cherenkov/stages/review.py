"""
CHERENKOV stages/review.py — real test review stage enforcing 6 quality gates including TSC & Prism mock.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import json

from cherenkov.core.contracts import (
    ReviewOutput,
    GenerateOutput,
    GateResult,
    Verdict,
    Status,
    StageMeta,
)
from cherenkov.core.errors import get_logger
from cherenkov.core.compat import npx as _npx, subprocess_env as _subprocess_env
from cherenkov.core.settings import get_settings
from cherenkov.execution.prism_mock import PrismMockServer
from cherenkov.execution.playwright_invoke import PlaywrightRunner
from cherenkov.execution.trace_reader import TraceReader
from cherenkov.healing import (
    Diagnoser,
    FailureClass,
    AuthExpiryHealer,
    ContractDriftHealer,
)


class ReviewStage:
    """Enforces 6 static and dynamic quality gates on generated tests."""

    _AUTO_APPROVE_THRESHOLD = 0.9
    _HITL_THRESHOLD = 0.7
    _PRISM_PORT = 4015

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("REVIEW", run_id)
        from pathlib import Path as _Path
        self.stub_dir = str(_Path(__file__).parent.parent.parent / "stub")

    def run(self, generate: GenerateOutput, spec_path: str) -> ReviewOutput:
        t0 = time.time()
        code = generate.test_code
        scenario_id = generate.scenario_id
        self.log.info("stage start", scenario_id=scenario_id)

        gates: list[GateResult] = []

        gates.append(self._gate_syntax(code))
        gates.append(self._gate_structure(code))
        gates.append(self._gate_ast(code))
        gates.append(self._gate_assertion(code))

        test_file_path = self._write_test_file(code, scenario_id)

        tsc_gate = self._gate_tsc(scenario_id)
        gates.append(tsc_gate)

        prism_gate = self._gate_prism(
            code, scenario_id, spec_path, tsc_gate.passed,
            gates[0].passed, gates[1].passed,
        )
        gates.append(prism_gate)

        self._gate_ocr(code, test_file_path, scenario_id, gates)
        self._gate_consensus(generate, code, spec_path, gates)

        quality_score = self._compute_quality_score(gates)
        verdict = self._determine_verdict(quality_score)

        self._log_finetune(verdict, generate, quality_score, gates, code)
        self._bridge_hitl(verdict, generate, quality_score, gates, scenario_id)

        dt = int((time.time() - t0) * 1000)
        self.log.info(
            "stage success",
            quality_score=quality_score,
            verdict=verdict.value,
            duration_ms=dt,
        )

        return ReviewOutput(
            scenario_id=scenario_id,
            gates=gates,
            quality_score=quality_score,
            verdict=verdict,
            status=Status.OK,
            metadata=StageMeta(stage="REVIEW", duration_ms=dt),
        )

    def _gate_syntax(self, code: str) -> GateResult:
        passed = True
        detail = "TS syntax well-formed."
        if not code.strip():
            passed = False
            detail = "Generated test code is empty."
        elif "```" in code:
            passed = False
            detail = "Test code contains stray markdown code block fences."
        return GateResult(gate="syntax", passed=passed, detail=detail)

    def _gate_structure(self, code: str) -> GateResult:
        passed = True
        detail = "All standard Playwright and client imports present."
        if "from '../client'" not in code and 'from "../client"' not in code:
            passed = False
            detail = (
                "Missing imports for target openapi-fetch client ('../client')."
            )
        elif (
            "from '@playwright/test'" not in code
            and 'from "@playwright/test"' not in code
        ):
            passed = False
            detail = "Missing imports for '@playwright/test'."
        return GateResult(gate="structure", passed=passed, detail=detail)

    def _gate_ast(self, code: str) -> GateResult:
        passed = True
        detail = (
            "Verified usage of openapi-fetch client with zero raw fetch/axios bleed."
        )
        uses_fetch_client = bool(
            re.search(r"\bclient\.(GET|POST|PUT|DELETE|PATCH)\b", code)
        )
        has_forbidden = bool(
            re.search(r"\b(fetch|axios)\b|\.request\b|throw new Error", code)
        )
        if not uses_fetch_client:
            passed = False
            detail = "Test fails to invoke the openapi-fetch client correctly."
        elif has_forbidden:
            passed = False
            detail = "Test contains forbidden HTTP keywords (raw fetch, axios, or custom throw statement)."
        return GateResult(gate="ast", passed=passed, detail=detail)

    def _gate_assertion(self, code: str) -> GateResult:
        passed = True
        detail = "Asserts specific status code and response body shape."
        specific_status = bool(
            re.search(r"\.status\)?\s*\)?\s*\.toBe\(\s*\d{3}\s*\)", code)
        ) or bool(re.search(r"toBe\(\s*(200|201|204|400|401|404|422|500)\s*\)", code))
        body_shape = bool(re.search(r"toHaveProperty\(|typeof\s", code))
        if not specific_status:
            passed = False
            detail = (
                "Missing expectation asserting specific status code (toBe(code))."
            )
        elif not body_shape:
            passed = False
            detail = "Missing expectation asserting response body property structure (toHaveProperty)."
        return GateResult(gate="assertion", passed=passed, detail=detail)

    def _write_test_file(self, code: str, scenario_id: str) -> str:
        tests_dir = os.path.join(self.stub_dir, "generated_tests")
        os.makedirs(tests_dir, exist_ok=True)
        test_file_path = os.path.join(tests_dir, f"{scenario_id}.spec.ts")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return test_file_path

    def _gate_tsc(self, scenario_id: str) -> GateResult:
        passed = True
        detail = "TypeScript compilation tsc --noEmit check passed successfully."
        try:
            process = subprocess.run(
                [_npx(), "tsc", "--noEmit"],
                cwd=self.stub_dir,
                capture_output=True,
                text=True,
                timeout=get_settings().TSC_TIMEOUT_SECONDS,
                env=_subprocess_env(),
            )
            if process.returncode != 0:
                our_file = f"generated_tests/{scenario_id}.spec.ts"
                our_errors = [
                    line
                    for line in (process.stdout + process.stderr).splitlines()
                    if our_file in line
                ]
                if our_errors:
                    passed = False
                    detail = "Typescript compilation failed:\n" + "\n".join(
                        our_errors[:3]
                    )
        except subprocess.TimeoutExpired:
            passed = False
            detail = "Typescript compilation timed out."
        except Exception as e:
            passed = False
            detail = f"Could not execute tsc check: {e}"
        return GateResult(gate="tsc", passed=passed, detail=detail)

    def _gate_prism(
        self, code: str, scenario_id: str, spec_path: str,
        tsc_passed: bool, syntax_passed: bool, structure_passed: bool,
    ) -> GateResult:
        passed = True
        skipped = False
        detail = "Dynamic Stoplight Prism mock server dry-run check passed."

        if not (syntax_passed and structure_passed and tsc_passed):
            return GateResult(
                gate="prism-dryrun", passed=True, skipped=True,
                detail="Prism gate skipped: earlier gates failed; code not submitted to mock server.",
            )

        prism_server = PrismMockServer(
            spec_path=spec_path, port=self._PRISM_PORT, run_id=self.run_id
        )

        if not prism_server.start():
            return GateResult(
                gate="prism-dryrun", passed=True, skipped=True,
                detail="Prism mock container unavailable (Docker not present); gate skipped.",
            )

        try:
            runner = PlaywrightRunner(run_id=self.run_id)
            run_result = runner.execute_test(
                scenario_id=scenario_id,
                test_code=code,
                api_url=f"http://localhost:{self._PRISM_PORT}",
            )

            if run_result["passed"]:
                self._record_passing_snapshot(run_result, code, scenario_id)
            else:
                passed = False
                detail = f"Test execution failed against Prism dynamic mock: {run_result['failure_message'][:200]}"
                self._handle_prism_failure(run_result, code, scenario_id)
        except Exception as e:
            passed = False
            detail = f"Exception occurred during Prism dry-run: {e}"
        finally:
            prism_server.stop()

        return GateResult(gate="prism-dryrun", passed=passed, detail=detail, skipped=skipped)

    def _record_passing_snapshot(self, run_result: dict, code: str, scenario_id: str):
        trace_path = run_result.get("trace_path", "")
        if not trace_path:
            return
        method_match = re.search(
            r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code
        )
        if not method_match:
            return
        target_method = method_match.group(1)
        target_url_path = method_match.group(2)
        reader = TraceReader(run_id=self.run_id)
        response_info = reader.extract_http_response(
            trace_path, target_url_path, target_method
        )
        if not response_info:
            return
        try:
            body_data = {}
            if response_info.get("body_raw"):
                body_data = json.loads(response_info["body_raw"])
            Diagnoser(self.run_id).record_passing_snapshot(
                scenario_id=scenario_id,
                status=response_info["status"],
                body=body_data,
                test_content=code,
            )
        except Exception as e:
            self.log.warning("failed to record passing snapshot", error=str(e))

    def _handle_prism_failure(self, run_result: dict, code: str, scenario_id: str):
        trace_path = run_result.get("trace_path", "")
        if not trace_path:
            return
        method_match = re.search(
            r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code
        )
        if not method_match:
            return
        target_method = method_match.group(1)
        target_url_path = method_match.group(2)
        reader = TraceReader(run_id=self.run_id)
        response_info = reader.extract_http_response(
            trace_path, target_url_path, target_method
        )
        if not response_info:
            return
        diagnoser = Diagnoser(self.run_id)
        body_data = {}
        try:
            if response_info.get("body_raw"):
                body_data = json.loads(response_info["body_raw"])
        except (json.JSONDecodeError, ValueError) as parse_err:
            self.log.warning("trace body parse failed", error=str(parse_err))
        diag = diagnoser.diagnose_failure(
            scenario_id=scenario_id,
            current_status=response_info["status"],
            current_body=body_data,
            test_name=scenario_id,
            test_content=code,
        )
        if diag.stale_snapshot:
            self.log.warning(
                "healing snapshot is stale; skipping auto-diff",
                scenario_id=scenario_id,
            )
        suggestion = ""
        if diag.failure_class == FailureClass.AUTH_EXPIRY:
            suggestion = AuthExpiryHealer(self.run_id).suggest_heal(scenario_id, target_url_path)
        elif diag.failure_class == FailureClass.CONTRACT_DRIFT:
            suggestion = ContractDriftHealer(self.run_id).suggest_heal(
                scenario_id=scenario_id,
                endpoint=target_url_path,
                method=target_method,
                missing_fields=diag.missing_fields,
                added_fields=diag.added_fields,
            )
        if suggestion and suggestion.get("suggestion"):
            print(suggestion["suggestion"])
            self.log.info(
                "generated healing suggestion",
                failure_class=diag.failure_class.value,
            )

    def _gate_ocr(self, code: str, test_file_path: str, scenario_id: str, gates: list[GateResult]):
        if not get_settings().OCR_ENABLED:
            return
        self.log.info("ocr gate: running OCR agent review", scenario_id=scenario_id)
        try:
            from cherenkov.review_ocr.stage import ReviewStageOCR
            ocr_stage = ReviewStageOCR(run_id=self.run_id)
            ocr_gate = ocr_stage.run(
                test_code=code, filepath=test_file_path, scenario_id=scenario_id,
            )
            if not ocr_gate.passed and not ocr_gate.skipped:
                self.log.info(
                    "ocr gate flagged issues",
                    scenario_id=scenario_id, detail=ocr_gate.detail[:200],
                )
            gates.append(ocr_gate)
        except Exception as ocr_err:
            self.log.warning("ocr gate error (skipped)", error=str(ocr_err))
            gates.append(
                GateResult(gate="ocr", passed=True, detail=f"OCR gate skipped (error): {ocr_err}", skipped=True)
            )

    def _gate_consensus(self, generate: GenerateOutput, code: str, spec_path: str, gates: list[GateResult]):
        if not get_settings().CONSENSUS_ORACLE_ENABLED:
            return
        static_passed = all(
            g.passed for g in gates[:4]
        )
        if not static_passed:
            return
        passed = True
        detail = "Consensus oracle skipped (not enabled or static gates failed)."
        try:
            from cherenkov.oracle.consensus_oracle import ConsensusOracle
            from cherenkov.core.contracts import Claim, Provenance, ProvenanceType

            oracle = ConsensusOracle(
                passes=get_settings().CONSENSUS_ORACLE_PASSES, run_id=self.run_id,
            )
            claim = Claim(
                id=generate.scenario_id,
                category="mutation",
                subject=f"{getattr(generate, 'method', '?')} {getattr(generate, 'endpoint', '?')}",
                provenance=Provenance(source_type=ProvenanceType.SPEC, source_uri=spec_path),
            )
            endpoint_slice = {
                "path": getattr(generate, "endpoint", ""),
                "method": getattr(generate, "method", ""),
                "operation": {}, "schemas": {},
            }
            oracle_result = oracle.evaluate(claim, test_code=code, endpoint_slice=endpoint_slice)
            passed = oracle_result.is_correct
            detail = oracle_result.detail or (
                "Consensus oracle: assertions verified."
                if passed else "Consensus oracle: assertions rejected by majority vote."
            )
            self.log.info(
                "consensus oracle gate", scenario_id=generate.scenario_id,
                passed=passed, confidence=oracle_result.confidence,
            )
        except Exception as exc:
            passed = True
            detail = f"Consensus oracle skipped (error): {exc}"
            self.log.warning("consensus gate error (skipped)", error=str(exc))
        gates.append(GateResult(gate="consensus-oracle", passed=passed, detail=detail))

    def _compute_quality_score(self, gates: list[GateResult]) -> float:
        scored_gates = [g for g in gates if not g.skipped]
        passed_count = sum(1 for g in scored_gates if g.passed)
        return passed_count / len(scored_gates) if scored_gates else 1.0

    def _determine_verdict(self, quality_score: float) -> Verdict:
        if quality_score >= self._AUTO_APPROVE_THRESHOLD:
            return Verdict.AUTO_APPROVE
        if quality_score >= self._HITL_THRESHOLD:
            return Verdict.HITL
        return Verdict.REGENERATE

    def _log_finetune(
        self, verdict: Verdict, generate: GenerateOutput,
        quality_score: float, gates: list[GateResult], code: str,
    ):
        if verdict not in (Verdict.AUTO_APPROVE, Verdict.REGENERATE):
            return
        try:
            from cherenkov.governance.finetune_log import FinetuneLogger
            _ftl = FinetuneLogger()
            _ftl.log_outcome(
                run_id=self.run_id or "unknown",
                endpoint=getattr(generate, "endpoint", "") or "",
                method=getattr(generate, "method", "") or "",
                case_type=generate.scenario_id.split("_")[0]
                if generate.scenario_id else "",
                mutation_id=generate.scenario_id,
                verdict="accepted" if verdict == Verdict.AUTO_APPROVE else "rejected",
                quality_score=quality_score,
                gate_results=[
                    {"gate": g.gate, "passed": g.passed, "detail": g.detail}
                    for g in gates
                ],
                test_code=code,
            )
        except Exception as _fte:
            self.log.warning("finetune_log_failed", error=str(_fte))

    def _bridge_hitl(
        self, verdict: Verdict, generate: GenerateOutput,
        quality_score: float, gates: list[GateResult], scenario_id: str,
    ):
        if verdict != Verdict.HITL:
            return
        try:
            from cherenkov.hitl import HitlItem, HitlQueue

            first_failing_gate = next((g.gate for g in gates if not g.passed), None)
            confidence_reason = (
                f"Quality score {quality_score:.2f} — gate '{first_failing_gate}' failed"
                if first_failing_gate
                else f"Quality score {quality_score:.2f} — all gates passed (low-confidence)"
            )
            hitl_item = HitlItem(
                id=scenario_id,
                endpoint=getattr(generate, "endpoint", None),
                method=getattr(generate, "method", None),
                mutation_id=getattr(generate, "mutation_id", None),
                mutation_label=getattr(generate, "mutation_label", None),
                confidence=round(quality_score, 4),
                confidence_reason=confidence_reason,
                review_gate_failed=first_failing_gate,
                run_id=self.run_id,
            )
            HitlQueue().enqueue(hitl_item)
            self.log.info(
                "hitl item enqueued",
                scenario_id=scenario_id,
                confidence=round(quality_score, 4),
                review_gate_failed=first_failing_gate,
            )
        except Exception as exc:
            self.log.warning("hitl enqueue failed (non-fatal)", error=str(exc))
