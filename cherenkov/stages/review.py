"""
CHERENKOV stages/review.py — real test review stage enforcing 6 quality gates including TSC & Prism mock.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
import json

from cherenkov.core.contracts import ReviewOutput, GenerateOutput, GateResult, Verdict, Status, StageMeta
from cherenkov.core.errors import get_logger
from cherenkov.core.compat import npx as _npx
from cherenkov.execution.prism_mock import PrismMockServer
from cherenkov.execution.playwright_invoke import PlaywrightRunner
from cherenkov.execution.trace_reader import TraceReader
from cherenkov.healing import Diagnoser, FailureClass, AuthExpiryHealer, ContractDriftHealer

class ReviewStage:
    """Enforces 6 static and dynamic quality gates (syntax, structure, AST, assertions, TSC, and Prism mock dry-run) on generated tests."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("REVIEW", run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))

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
        gates.append(GateResult(gate="syntax", passed=syntax_passed, detail=syntax_detail))

        # 2. Structure Gate (Imports verification)
        structure_passed = True
        structure_detail = "All standard Playwright and client imports present."
        if "from '../client'" not in code and 'from "../client"' not in code:
            structure_passed = False
            structure_detail = "Missing imports for target openapi-fetch client ('../client')."
        elif "from '@playwright/test'" not in code and 'from "@playwright/test"' not in code:
            structure_passed = False
            structure_detail = "Missing imports for '@playwright/test'."
        gates.append(GateResult(gate="structure", passed=structure_passed, detail=structure_detail))

        # 3. AST-validate Gate (Direct openapi-fetch client calls only)
        ast_passed = True
        ast_detail = "Verified usage of openapi-fetch client with zero raw fetch/axios bleed."
        uses_fetch_client = bool(re.search(r"\bclient\.(GET|POST|PUT|DELETE|PATCH)\b", code))
        has_forbidden = bool(re.search(r"\b(fetch|axios)\b|\.request\b|throw new Error", code))
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
        specific_status = bool(re.search(r"\.status\)?\s*\)?\s*\.toBe\(\s*\d{3}\s*\)", code)) or \
                          bool(re.search(r"toBe\(\s*(200|201|204|400|401|404|422|500)\s*\)", code))
        body_shape = bool(re.search(r"toHaveProperty\(|typeof\s", code))
        if not specific_status:
            assertions_passed = False
            assertions_detail = "Missing expectation asserting specific status code (toBe(code))."
        elif not body_shape:
            assertions_passed = False
            assertions_detail = "Missing expectation asserting response body property structure (toHaveProperty)."
        gates.append(GateResult(gate="assertion", passed=assertions_passed, detail=assertions_detail))

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
            # We run tsc --noEmit in the stub folder
            process = subprocess.run(
                [_npx(), "tsc", "--noEmit"],
                cwd=self.stub_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if process.returncode != 0:
                tsc_passed = False
                # Grab first 150 characters of compilation errors
                tsc_detail = f"Typescript compilation failed:\n{process.stderr[:150]}"
        except subprocess.TimeoutExpired:
            tsc_passed = False
            tsc_detail = "Typescript compilation timed out."
        except Exception as e:
            tsc_passed = False
            tsc_detail = f"Could not execute tsc check: {e}"
            
        gates.append(GateResult(gate="tsc", passed=tsc_passed, detail=tsc_detail))

        # 6. Gate 6 — Prism dynamic-mode dry-run (Ephemerally spins stoplight/prism in Docker)
        prism_passed = True
        prism_detail = "Dynamic Stoplight Prism mock server dry-run check passed."
        
        if syntax_passed and structure_passed and tsc_passed:
            prism_port = 4015  # Use port 4015 to prevent conflict
            prism_server = PrismMockServer(spec_path=spec_path, port=prism_port, run_id=self.run_id)
            
            # Start Prism container
            if prism_server.start():
                try:
                    runner = PlaywrightRunner(run_id=self.run_id)
                    run_result = runner.execute_test(
                        scenario_id=scenario_id,
                        test_code=code,
                        api_url=f"http://localhost:{prism_port}"
                    )
                    
                    if run_result["passed"]:
                        # Capture passing snapshot for healing reference
                        trace_path = run_result.get("trace_path", "")
                        if trace_path:
                            reader = TraceReader(run_id=self.run_id)
                            method_match = re.search(r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code)
                            if method_match:
                                target_method = method_match.group(1)
                                target_url_path = method_match.group(2)
                                response_info = reader.extract_http_response(trace_path, target_url_path, target_method)
                                if response_info:
                                    try:
                                        body_data = {}
                                        if response_info.get("body_raw"):
                                            body_data = json.loads(response_info["body_raw"])
                                        Diagnoser(self.run_id).record_passing_snapshot(
                                            scenario_id=scenario_id,
                                            status=response_info["status"],
                                            body=body_data,
                                            test_content=code
                                        )
                                    except Exception as e:
                                        self.log.warning("failed to record passing snapshot", error=str(e))
                    else:
                        prism_passed = False
                        prism_detail = f"Test execution failed against Prism dynamic mock: {run_result['failure_message'][:200]}"
                        
                        # Programmatically parse trace.zip on failure to extract http response details
                        trace_path = run_result.get("trace_path", "")
                        if trace_path:
                            reader = TraceReader(run_id=self.run_id)
                            # Find the HTTP method and url path in the code to search the trace
                            method_match = re.search(r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code)
                            if method_match:
                                target_method = method_match.group(1)
                                target_url_path = method_match.group(2)
                                response_info = reader.extract_http_response(trace_path, target_url_path, target_method)
                                
                                if response_info:
                                    # Diagnose failure
                                    diagnoser = Diagnoser(self.run_id)
                                    body_data = {}
                                    try:
                                        if response_info.get("body_raw"):
                                            body_data = json.loads(response_info["body_raw"])
                                    except Exception:
                                        pass
                                    
                                    diag = diagnoser.diagnose_failure(
                                        scenario_id=scenario_id,
                                        current_status=response_info["status"],
                                        current_body=body_data,
                                        test_name=scenario_id,
                                        test_content=code
                                    )

                                    if diag.stale_snapshot:
                                        self.log.warning(
                                            "healing snapshot is stale; skipping auto-diff",
                                            scenario_id=scenario_id,
                                        )
                                    
                                    # Run Healers (Suggest-only!)
                                    suggestion = ""
                                    if diag.failure_class == FailureClass.AUTH_EXPIRY:
                                        suggestion = AuthExpiryHealer(self.run_id).suggest_heal(scenario_id, target_url_path)
                                    elif diag.failure_class == FailureClass.CONTRACT_DRIFT:
                                        suggestion = ContractDriftHealer(self.run_id).suggest_heal(
                                            scenario_id=scenario_id,
                                            endpoint=target_url_path,
                                            method=target_method,
                                            missing_fields=diag.missing_fields,
                                            added_fields=diag.added_fields
                                        )
                                    
                                    if suggestion and suggestion.get("suggestion"):
                                        print(suggestion["suggestion"])
                                        self.log.info("generated healing suggestion", failure_class=diag.failure_class.value)
                                        try:
                                            from cherenkov.openclaw.adapter import OpenClawAdapter
                                            OpenClawAdapter().notify_healing_suggestion({
                                                "scenario_id": scenario_id,
                                                "suggestion": suggestion["suggestion"],
                                                "failure_class": diag.failure_class.value
                                            })
                                        except Exception as exc:
                                            self.log.warning("failed to emit slack notification for healing suggestion", error=str(exc))
                except Exception as e:
                    prism_passed = False
                    prism_detail = f"Exception occurred during Prism dry-run: {e}"
                finally:
                    # Tear down Prism container
                    prism_server.stop()
            else:
                prism_passed = False
                prism_detail = "Failed to start Stoplight Prism mock container."
        else:
            prism_passed = False
            prism_detail = "Skipped Prism mock server check due to failing syntax, structure, or compilation gates."
            
        gates.append(GateResult(gate="prism-dryrun", passed=prism_passed, detail=prism_detail))

        # Calculate quality score as fraction of passed gates
        passed_count = sum(1 for g in gates if g.passed)
        quality_score = passed_count / len(gates)

        # Enforce Verdict thresholds
        if quality_score >= 0.9:
            verdict = Verdict.AUTO_APPROVE
        elif quality_score >= 0.7:
            verdict = Verdict.HITL
        else:
            verdict = Verdict.REGENERATE

        # A2 #110 — bridge: Verdict.HITL → HitlQueue.enqueue
        # Only fires on HITL (0.7–0.9 quality band), never on REGENERATE or AUTO_APPROVE.
        # Lazy import avoids circular imports at module load time.
        if verdict == Verdict.HITL:
            try:
                from cherenkov.hitl import HitlItem, HitlQueue  # lazy import
                first_failing_gate = next(
                    (g.gate for g in gates if not g.passed), None
                )
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
                try:
                    from cherenkov.openclaw.adapter import OpenClawAdapter
                    OpenClawAdapter().notify_new_item(hitl_item)
                except Exception as exc:
                    self.log.warning("failed to emit slack notification for new hitl item", error=str(exc))
                self.log.info(
                    "hitl item enqueued",
                    scenario_id=scenario_id,
                    confidence=round(quality_score, 4),
                    review_gate_failed=first_failing_gate,
                )
            except Exception as exc:  # never let HITL bridging break REVIEW
                self.log.warning("hitl enqueue failed (non-fatal)", error=str(exc))

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", quality_score=quality_score, verdict=verdict.value, duration_ms=dt)

        return ReviewOutput(
            scenario_id=scenario_id,
            gates=gates,
            quality_score=quality_score,
            verdict=verdict,
            status=Status.OK,
            metadata=StageMeta(stage="REVIEW", duration_ms=dt)
        )
