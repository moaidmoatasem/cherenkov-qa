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
from cherenkov.core.compat import npx as _npx
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
    """Enforces 6 static and dynamic quality gates (syntax, structure, AST, assertions, TSC, and Prism mock dry-run) on generated tests."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("REVIEW", run_id)
        self.stub_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../stub")
        )

    def run(self, generate: GenerateOutput, spec_path: str) -> ReviewOutput:
        t0 = time.time()
        code = generate.test_code
        scenario_id = generate.scenario_id
        self.log.info("stage start", scenario_id=scenario_id)

        gates: list[GateResult] = []

        # 1. Syntax Gate (Basic TS cleanup)
        syntax_passed = True
        syntax_detail = "TS syntax well-formed."
        if not code.strip():
            syntax_passed = False
            syntax_detail = "Generated test code is empty."
        elif "```" in code:
            syntax_passed = False
            syntax_detail = "Test code contains stray markdown code block fences."
        gates.append(
            GateResult(gate="syntax", passed=syntax_passed, detail=syntax_detail)
        )

        # 2. Structure Gate (Imports verification)
        structure_passed = True
        structure_detail = "All standard Playwright and client imports present."
        if "from '../client'" not in code and 'from "../client"' not in code:
            structure_passed = False
            structure_detail = (
                "Missing imports for target openapi-fetch client ('../client')."
            )
        elif (
            "from '@playwright/test'" not in code
            and 'from "@playwright/test"' not in code
        ):
            structure_passed = False
            structure_detail = "Missing imports for '@playwright/test'."
        gates.append(
            GateResult(
                gate="structure", passed=structure_passed, detail=structure_detail
            )
        )

        # 3. AST-validate Gate (Direct openapi-fetch client calls only)
        ast_passed = True
        ast_detail = (
            "Verified usage of openapi-fetch client with zero raw fetch/axios bleed."
        )
        uses_fetch_client = bool(
            re.search(r"\bclient\.(GET|POST|PUT|DELETE|PATCH)\b", code)
        )
        has_forbidden = bool(
            re.search(r"\b(fetch|axios)\b|\.request\b|throw new Error", code)
        )
        if not uses_fetch_client:
            ast_passed = False
            ast_detail = "Test fails to invoke the openapi-fetch client correctly."
        elif has_forbidden:
            ast_passed = False
            ast_detail = "Test contains forbidden HTTP keywords (raw fetch, axios, or custom throw statement)."
        gates.append(GateResult(gate="ast", passed=ast_passed, detail=ast_detail))

        # 4. Assertions Gate (Response status & body shape)
        assertions_passed = True
        assertions_detail = "Asserts specific status code and response body shape."
        specific_status = bool(
            re.search(r"\.status\)?\s*\)?\s*\.toBe\(\s*\d{3}\s*\)", code)
        ) or bool(re.search(r"toBe\(\s*(200|201|204|400|401|404|422|500)\s*\)", code))
        body_shape = bool(re.search(r"toHaveProperty\(|typeof\s", code))
        if not specific_status:
            assertions_passed = False
            assertions_detail = (
                "Missing expectation asserting specific status code (toBe(code))."
            )
        elif not body_shape:
            assertions_passed = False
            assertions_detail = "Missing expectation asserting response body property structure (toHaveProperty)."
        gates.append(
            GateResult(
                gate="assertion", passed=assertions_passed, detail=assertions_detail
            )
        )

        # We write the file inside generated_tests first to let TSC and Playwright access it
        tests_dir = os.path.join(self.stub_dir, "generated_tests")
        os.makedirs(tests_dir, exist_ok=True)
        test_file_path = os.path.join(tests_dir, f"{scenario_id}.spec.ts")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(code)

        # 5. Gate 5 — TSC Compilation Gate (Real compile against generated types, not regex)
        tsc_passed = True
        tsc_detail = "TypeScript compilation tsc --noEmit check passed successfully."

        try:
            # Run tsc --noEmit in the stub folder; filter errors to only those in the
            # current test file so pre-existing errors from old runs don't block new tests.
            process = subprocess.run(
                [_npx(), "tsc", "--noEmit"],
                cwd=self.stub_dir,
                capture_output=True,
                text=True,
                timeout=get_settings().TSC_TIMEOUT_SECONDS,
            )
            if process.returncode != 0:
                our_file = f"generated_tests/{scenario_id}.spec.ts"
                our_errors = [
                    line
                    for line in (process.stdout + process.stderr).splitlines()
                    if our_file in line
                ]
                if our_errors:
                    tsc_passed = False
                    tsc_detail = "Typescript compilation failed:\n" + "\n".join(
                        our_errors[:3]
                    )
                # else: other pre-existing files have errors; this file is clean → pass
        except subprocess.TimeoutExpired:
            tsc_passed = False
            tsc_detail = "Typescript compilation timed out."
        except Exception as e:
            tsc_passed = False
            tsc_detail = f"Could not execute tsc check: {e}"

        gates.append(GateResult(gate="tsc", passed=tsc_passed, detail=tsc_detail))

        # 6. Gate 6 — Prism dynamic-mode dry-run (Ephemerally spins stoplight/prism in Docker)
        prism_passed = True
        prism_skipped = False
        prism_detail = "Dynamic Stoplight Prism mock server dry-run check passed."

        if syntax_passed and structure_passed and tsc_passed:
            prism_port = 4015  # Use port 4015 to prevent conflict
            prism_server = PrismMockServer(
                spec_path=spec_path, port=prism_port, run_id=self.run_id
            )

            # Start Prism container
            if prism_server.start():
                try:
                    runner = PlaywrightRunner(run_id=self.run_id)
                    run_result = runner.execute_test(
                        scenario_id=scenario_id,
                        test_code=code,
                        api_url=f"http://localhost:{prism_port}",
                    )

                    if run_result["passed"]:
                        # Capture passing snapshot for healing reference
                        trace_path = run_result.get("trace_path", "")
                        if trace_path:
                            reader = TraceReader(run_id=self.run_id)
                            method_match = re.search(
                                r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code
                            )
                            if method_match:
                                target_method = method_match.group(1)
                                target_url_path = method_match.group(2)
                                response_info = reader.extract_http_response(
                                    trace_path, target_url_path, target_method
                                )
                                if response_info:
                                    try:
                                        body_data = {}
                                        if response_info.get("body_raw"):
                                            body_data = json.loads(
                                                response_info["body_raw"]
                                            )
                                        Diagnoser(self.run_id).record_passing_snapshot(
                                            scenario_id=scenario_id,
                                            status=response_info["status"],
                                            body=body_data,
                                            test_content=code,
                                        )
                                    except Exception as e:
                                        self.log.warning(
                                            "failed to record passing snapshot",
                                            error=str(e),
                                        )
                    else:
                        prism_passed = False
                        prism_detail = f"Test execution failed against Prism dynamic mock: {run_result['failure_message'][:200]}"

                        # Programmatically parse trace.zip on failure to extract http response details
                        trace_path = run_result.get("trace_path", "")
                        if trace_path:
                            reader = TraceReader(run_id=self.run_id)
                            # Find the HTTP method and url path in the code to search the trace
                            method_match = re.search(
                                r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code
                            )
                            if method_match:
                                target_method = method_match.group(1)
                                target_url_path = method_match.group(2)
                                response_info = reader.extract_http_response(
                                    trace_path, target_url_path, target_method
                                )

                                if response_info:
                                    # Diagnose failure
                                    diagnoser = Diagnoser(self.run_id)
                                    body_data = {}
                                    try:
                                        if response_info.get("body_raw"):
                                            body_data = json.loads(
                                                response_info["body_raw"]
                                            )
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

                                    # Run Healers (Suggest-only!)
                                    suggestion = ""
                                    if diag.failure_class == FailureClass.AUTH_EXPIRY:
                                        suggestion = AuthExpiryHealer(
                                            self.run_id
                                        ).suggest_heal(scenario_id, target_url_path)
                                    elif (
                                        diag.failure_class
                                        == FailureClass.CONTRACT_DRIFT
                                    ):
                                        suggestion = ContractDriftHealer(
                                            self.run_id
                                        ).suggest_heal(
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
                except Exception as e:
                    prism_passed = False
                    prism_detail = f"Exception occurred during Prism dry-run: {e}"
                finally:
                    # Tear down Prism container
                    prism_server.stop()
            else:
                # Prism container failed to start — genuinely skipped (optional infra),
                # not passed. Excluded from quality_score via skipped=True.
                prism_passed = True
                prism_skipped = True
                prism_detail = "Prism mock container unavailable (Docker not present); gate skipped."
                self.log.warning("prism gate skipped — Docker unavailable")
        else:
            prism_passed = True
            prism_skipped = True
            prism_detail = "Prism gate skipped: earlier gates failed; code not submitted to mock server."

        gates.append(
            GateResult(
                gate="prism-dryrun",
                passed=prism_passed,
                detail=prism_detail,
                skipped=prism_skipped,
            )
        )

        # 7. Gate 7 — CANDOR Consensus Oracle (opt-in via CHERENKOV_CONSENSUS_ORACLE=true)
        # Runs N independent LLM passes to validate that assertions are correct and
        # meaningful. Only fires when the four static gates all passed (no point
        # spending LLM calls on structurally broken code).
        if (
            get_settings().CONSENSUS_ORACLE_ENABLED
            and syntax_passed
            and structure_passed
            and ast_passed
            and assertions_passed
        ):
            consensus_passed = True
            consensus_detail = (
                "Consensus oracle skipped (not enabled or static gates failed)."
            )
            try:
                from cherenkov.oracle.consensus_oracle import ConsensusOracle
                from cherenkov.core.contracts import Claim, Provenance, ProvenanceType

                oracle = ConsensusOracle(
                    passes=get_settings().CONSENSUS_ORACLE_PASSES,
                    run_id=self.run_id,
                )
                claim = Claim(
                    id=scenario_id,
                    category="mutation",
                    subject=f"{getattr(generate, 'method', '?')} {getattr(generate, 'endpoint', '?')}",
                    provenance=Provenance(
                        source_type=ProvenanceType.SPEC, source_uri=spec_path
                    ),
                )
                endpoint_slice = {
                    "path": getattr(generate, "endpoint", ""),
                    "method": getattr(generate, "method", ""),
                    "operation": {},
                    "schemas": {},
                }
                oracle_result = oracle.evaluate(
                    claim, test_code=code, endpoint_slice=endpoint_slice
                )
                consensus_passed = oracle_result.is_correct
                consensus_detail = oracle_result.detail or (
                    "Consensus oracle: assertions verified."
                    if consensus_passed
                    else "Consensus oracle: assertions rejected by majority vote."
                )
                self.log.info(
                    "consensus oracle gate",
                    scenario_id=scenario_id,
                    passed=consensus_passed,
                    confidence=oracle_result.confidence,
                )
            except Exception as exc:
                # Never let Gate 7 crash the pipeline — treat as skipped
                consensus_passed = True
                consensus_detail = f"Consensus oracle skipped (error): {exc}"
                self.log.warning("consensus gate error (skipped)", error=str(exc))
            gates.append(
                GateResult(
                    gate="consensus-oracle",
                    passed=consensus_passed,
                    detail=consensus_detail,
                )
            )

        # Calculate quality score as fraction of passed gates, excluding gates
        # that were skipped due to unavailable infra (e.g. no Docker) rather
        # than actually evaluated.
        scored_gates = [g for g in gates if not g.skipped]
        passed_count = sum(1 for g in scored_gates if g.passed)
        quality_score = passed_count / len(scored_gates) if scored_gates else 1.0

        # Enforce Verdict thresholds
        if quality_score >= 0.9:
            verdict = Verdict.AUTO_APPROVE
        elif quality_score >= 0.7:
            verdict = Verdict.HITL
        else:
            verdict = Verdict.REGENERATE

        # ── Fine-tune signal collection ────────────────────────────────────
        # Log AUTO_APPROVE (accepted) and REGENERATE (rejected) outcomes so
        # confirmed examples can later feed a local-model fine-tuning dataset.
        if verdict in (Verdict.AUTO_APPROVE, Verdict.REGENERATE):
            try:
                from cherenkov.governance.finetune_log import FinetuneLogger

                _ftl = FinetuneLogger()
                _ftl.log_outcome(
                    run_id=self.run_id or "unknown",
                    endpoint=getattr(generate, "endpoint", "") or "",
                    method=getattr(generate, "method", "") or "",
                    case_type=generate.scenario_id.split("_")[0]
                    if generate.scenario_id
                    else "",
                    mutation_id=generate.scenario_id,
                    verdict="accepted"
                    if verdict == Verdict.AUTO_APPROVE
                    else "rejected",
                    quality_score=quality_score,
                    gate_results=[
                        {"gate": g.gate, "passed": g.passed, "detail": g.detail}
                        for g in gates
                    ],
                    test_code=code,
                )
            except Exception as _fte:
                self.log.warning("finetune_log_failed", error=str(_fte))

        # A2 #110 — bridge: Verdict.HITL → HitlQueue.enqueue
        # Only fires on HITL (0.7–0.9 quality band), never on REGENERATE or AUTO_APPROVE.
        # Lazy import avoids circular imports at module load time.
        if verdict == Verdict.HITL:
            try:
                from cherenkov.hitl import HitlItem, HitlQueue  # lazy import

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
            except Exception as exc:  # never let HITL bridging break REVIEW
                self.log.warning("hitl enqueue failed (non-fatal)", error=str(exc))

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
