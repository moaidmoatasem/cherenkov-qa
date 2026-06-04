"""
CHERENKOV core/orchestrator.py — real orchestration engine.
Authority: v3.1 + delta.

Wires the real E2E flow: INGEST -> PLAN -> GENERATE -> REVIEW.
Includes:
  - Versioned Pydantic contract validation at each stage boundary.
  - A retry ladder that attempts stage recovery on contract/logical errors.
  - A circuit breaker that trips when threshold limits are breached.
  - Real-time CLI progress view and JSONL structured logs.
  - Deliberate mutation test hooks to prove resilient fallback execution.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable, Any

from pydantic import ValidationError

from cherenkov.core.contracts import (
    VisualSlice, VisualReport,
    IngestOutput, PlanOutput, GenerateOutput, ReviewOutput,
    EndpointSlice, Mutation, Scenario, GateResult, Verdict, Status, StageMeta, StageError
)
from cherenkov.core.errors import get_logger, ContractError
from cherenkov.ai import get_accounting_report, get_cache_stats
from cherenkov.stages.ingest import IngestStage
from cherenkov.stages.plan import PlanStage
from cherenkov.stages.generate import GenerateStage
from cherenkov.stages.review import ReviewStage
from cherenkov.core.config import Config



class CircuitBreaker:
    """Simple stateful circuit breaker. Trips if error count exceeds threshold."""

    def __init__(self, threshold: int = 2):
        self.threshold = threshold
        self.error_count = 0
        self.tripped = False

    def record_failure(self):
        self.error_count += 1
        if self.error_count >= self.threshold:
            self.tripped = True

    def reset(self):
        self.error_count = 0
        self.tripped = False


class OrchestrationEngine:
    """The central execution engine orchestrating stages E2E."""

    def __init__(self, run_id: str | None = None, error_threshold: int = 2, event_callback: Callable[[str, dict], None] | None = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        
        # Setup run directory and events log (Issue 186)
        import os
        from cherenkov.core.errors import LoggerConfig
        run_dir = os.path.abspath(f".cherenkov/runs/{self.run_id}")
        os.makedirs(run_dir, exist_ok=True)
        LoggerConfig.events_file = open(os.path.join(run_dir, "events.jsonl"), "a", encoding="utf-8")
        
        self.log = get_logger("orchestrator", self.run_id)
        self.breaker = CircuitBreaker(threshold=error_threshold)
        self.last_ingest: IngestOutput | None = None
        self.event_callback = event_callback

    # ── Stage 1: INGEST Stage ──────────────────────────────────────────────
    def run_ingest(self, spec_path: str, simulate_malformed: bool = False) -> IngestOutput:
        self.log.info("stage run", stage="INGEST", spec_path=spec_path)
        
        # Test Mutation Trigger: return dict lacking required Fields (fails Pydantic schema validation)
        if simulate_malformed:
            return {
                "endpoints": [],
                "client_stub_path": "stub/client.ts"
            } # type: ignore
            
        ingest_output = IngestStage(self.run_id).run(spec_path)
        self.last_ingest = ingest_output
        return ingest_output

    # ── Stage 2: PLAN Stage ────────────────────────────────────────────────
    def run_plan(self, ingest: IngestOutput, simulate_malformed: bool = False) -> PlanOutput:
        self.log.info("stage run", stage="PLAN", endpoints_count=len(ingest.endpoints))
        
        if simulate_malformed:
            return {
                "scenarios": []
            } # type: ignore

        return PlanStage(self.run_id).run(ingest)

    # ── Stage 3: GENERATE Stage ────────────────────────────────────────────
    def run_generate(self, scenario: Scenario, simulate_malformed: bool = False) -> GenerateOutput:
        self.log.info("stage run", stage="GENERATE", scenario_id=scenario.mutation_id)
        
        if simulate_malformed:
            return {
                "scenario_id": scenario.mutation_id or "unknown",
                "test_code": ""
            } # type: ignore

        # Look up corresponding EndpointSlice from Stage 1 to obtain resolved operation & schemas
        endpoint_slice = None
        if self.last_ingest:
            for ep in self.last_ingest.endpoints:
                if ep.path == scenario.endpoint and ep.method.upper() == scenario.method.upper():
                    endpoint_slice = ep
                    break

        if not endpoint_slice:
            endpoint_slice = EndpointSlice(
                path=scenario.endpoint,
                method=scenario.method,
                operation={},
                schemas={},
                richness=0.5,
                mutations=[]
            )

        # Look up mutation instruction
        instruction = "Provide valid request payload."
        for mut in endpoint_slice.mutations:
            if mut.id == scenario.mutation_id:
                instruction = mut.instruction
                break

        return GenerateStage(self.run_id).run(
            scenario=scenario,
            path=endpoint_slice.path,
            method=endpoint_slice.method,
            operation=endpoint_slice.operation,
            schemas=endpoint_slice.schemas,
            instruction=instruction
        )

    # ── Stage 4: REVIEW Stage ──────────────────────────────────────────────
    def run_review(self, generate: GenerateOutput, spec_path: str, simulate_malformed: bool = False) -> ReviewOutput:
        self.log.info("stage run", stage="REVIEW", scenario_id=generate.scenario_id)
        
        if simulate_malformed:
            return {
                "scenario_id": generate.scenario_id,
                "gates": [],
                "quality_score": 0.0
            } # type: ignore

        return ReviewStage(self.run_id).run(generate, spec_path)


    # ── The Retry Ladder & Boundary Validator Wrapper ───────────────────────
    def _execute_stage_with_retry(
        self,
        stage_name: str,
        stage_func: Callable[[], Any],
        fallback_factory: Callable[[], Any]
    ) -> Any:
        """Executes a stage. On contract validation or stage errors, it triggers the
        retry ladder up to 2 times before falling back and recording a breaker count."""
        
        attempts = 0
        max_attempts = 3  # Initial + 2 retries
        
        while attempts < max_attempts:
            try:
                # 1. Execute stage logic
                result = stage_func()
                
                # 2. Strict boundary type check: If raw dict was returned by simulation, force validation
                if not isinstance(result, (IngestOutput, PlanOutput, GenerateOutput, ReviewOutput)):
                    raise ContractError(f"Stage {stage_name} returned unvalidated raw types.")
                
                # Success path
                self.log.info("stage success", stage=stage_name, duration_ms=result.metadata.duration_ms)
                return result
                
            except (ValidationError, ContractError, Exception) as e:
                attempts += 1
                self.log.warning(
                    "stage boundary violation",
                    stage=stage_name,
                    attempt=attempts,
                    error=str(e)
                )
                
                if attempts >= max_attempts:
                    # Retry ladder exhausted -> record failure on circuit breaker
                    self.log.error(
                        "retry ladder exhausted",
                        stage=stage_name,
                        detail="triggering fallback schema"
                    )
                    self.breaker.record_failure()
                    return fallback_factory()
                    
                time.sleep(0.1)  # Brief wait before retry

    # ── E2E Orchestration DAG ─────────────────────────────────────────────
    def run_pipeline(
        self,
        spec_path: str,
        simulate_fail_stage: str | None = None,
    ) -> bool:
        """Runs E2E pipeline, tracking progress on the CLI. Returns True on success."""
        # Dynamic GPU/CPU device detection health check at startup
        Config.detect_ollama_device(self.run_id)
        
        print(f"\n================ CHERENKOV PIPELINE RUN [{self.run_id}] ================")
        print("  INGEST  [ Waiting... ]")
        print("  PLAN    [ Waiting... ]")
        print("  GENERATE[ Waiting... ]")
        print("  REVIEW  [ Waiting... ]")
        print("========================================================\n")
        
        if self.event_callback:
            self.event_callback("stage_start", {"stage": "INGEST"})

        # 1. INGEST
        print("\033[F\033[F\033[F\033[F\033[F  INGEST  [ Running... ]")
        ingest = self._execute_stage_with_retry(
            "INGEST",
            lambda: self.run_ingest(spec_path, simulate_malformed=(simulate_fail_stage == "INGEST")),
            lambda: IngestOutput(
                endpoints=[],
                client_stub_path="stub/client.ts",
                status=Status.FAILED,
                errors=[StageError(code="INGEST_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage="INGEST", duration_ms=0)
            )
        )
        print(f"\033[F\033[F\033[F\033[F  INGEST  [ {ingest.status.upper()} ] ({ingest.metadata.duration_ms}ms)")

        if self.event_callback:
            self.event_callback("stage_success", {
                "stage": "INGEST",
                "summary": f"{len(ingest.endpoints)} endpoints indexed",
                "duration_ms": ingest.metadata.duration_ms
            })

        # Circuit Breaker check
        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            if self.event_callback:
                self.event_callback("pipeline_complete", {"success": False, "reason": "Circuit breaker tripped"})
            return False

        if self.event_callback:
            self.event_callback("stage_start", {"stage": "PLAN"})

        # 2. PLAN
        print("  PLAN    [ Running... ]")
        plan = self._execute_stage_with_retry(
            "PLAN",
            lambda: self.run_plan(ingest, simulate_malformed=(simulate_fail_stage == "PLAN")),
            lambda: PlanOutput(
                scenarios=[],
                status=Status.FAILED,
                errors=[StageError(code="PLAN_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage="PLAN", duration_ms=0)
            )
        )
        print(f"\033[F  PLAN    [ {plan.status.upper()} ] ({plan.metadata.duration_ms}ms)")

        if self.event_callback:
            self.event_callback("stage_success", {
                "stage": "PLAN",
                "summary": f"{len(plan.scenarios)} scenarios planned",
                "duration_ms": plan.metadata.duration_ms
            })

        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            if self.event_callback:
                self.event_callback("pipeline_complete", {"success": False, "reason": "Circuit breaker tripped"})
            return False

        # 3 & 4. GENERATE and REVIEW with D2 Planner Feedback loop (distinct from simple retry ladder)
        if not plan.scenarios:
            self.log.warning("no scenarios available", stage="PLAN")
            print("  GENERATE[ SKIPPED ]")
            print("  REVIEW  [ SKIPPED ]")
            if self.event_callback:
                self.event_callback("pipeline_complete", {"success": True})
            return True

        replans_per_endpoint = {}
        fails_per_case_type = {}
        
        scenario = plan.scenarios[0]
        current_scenario = scenario
        generate = None
        review = None
        
        if self.event_callback:
            self.event_callback("stage_start", {"stage": "GENERATE"})

        while True:
            print("  GENERATE[ Running... ]")
            generate = self._execute_stage_with_retry(
                "GENERATE",
                lambda: self.run_generate(current_scenario, simulate_malformed=(simulate_fail_stage == "GENERATE")),
                lambda: GenerateOutput(
                    scenario_id=current_scenario.mutation_id or "unknown",
                    test_code="",
                    imports=[],
                    status=Status.FAILED,
                    errors=[StageError(code="GENERATE_FALLBACK", detail="Failed after retry ladder.")],
                    metadata=StageMeta(stage="GENERATE", duration_ms=0)
                )
            )
            print(f"\033[F  GENERATE[ {generate.status.upper()} ] ({generate.metadata.duration_ms}ms)")

            if generate.status == Status.OK and self.event_callback:
                self.event_callback("test_generated", {
                    "endpoint": current_scenario.endpoint,
                    "method": current_scenario.method,
                    "code": generate.test_code,
                    "agent": "qwen2.5-coder:7b"
                })

            if self.breaker.tripped:
                self.log.error("pipeline aborted", reason="circuit breaker tripped")
                print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
                if self.event_callback:
                    self.event_callback("pipeline_complete", {"success": False, "reason": "Circuit breaker tripped"})
                return False

            if self.event_callback:
                self.event_callback("stage_start", {"stage": "REVIEW"})

            print("  REVIEW  [ Running... ]")
            review = self._execute_stage_with_retry(
                "REVIEW",
                lambda: self.run_review(generate, spec_path, simulate_malformed=(simulate_fail_stage == "REVIEW")),
                lambda: ReviewOutput(
                    scenario_id=generate.scenario_id,
                    gates=[],
                    quality_score=0.0,
                    verdict=Verdict.REGENERATE,
                    status=Status.FAILED,
                    errors=[StageError(code="REVIEW_FALLBACK", detail="Failed after retry ladder.")],
                    metadata=StageMeta(stage="REVIEW", duration_ms=0)
                )
            )
            print(f"\033[F  REVIEW  [ {review.status.upper()} ] ({review.metadata.duration_ms}ms)")

            if self.event_callback:
                self.event_callback("stage_success", {
                    "stage": "REVIEW",
                    "summary": f"Review complete with verdict: {review.verdict.upper()}",
                    "duration_ms": review.metadata.duration_ms
                })

            if self.breaker.tripped:
                self.log.error("pipeline aborted", reason="circuit breaker tripped")
                print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
                if self.event_callback:
                    self.event_callback("pipeline_complete", {"success": False, "reason": "Circuit breaker tripped"})
                return False

            # D2 Planner Feedback loop: if the prism dynamic dry-run fails, trigger dynamic re-planning
            prism_failed = any(g.gate == "prism-dryrun" and not g.passed for g in review.gates)
            if prism_failed:
                endpoint = current_scenario.endpoint
                case_type = current_scenario.case_type
                
                replans_per_endpoint[endpoint] = replans_per_endpoint.get(endpoint, 0) + 1
                fails_per_case_type[(endpoint, case_type)] = fails_per_case_type.get((endpoint, case_type), 0) + 1
                
                self.log.warning(
                    "D2 Planner Feedback loop triggered due to Prism dry-run failure",
                    endpoint=endpoint,
                    case_type=case_type,
                    failed_mutation=current_scenario.mutation_id,
                    replan_count=replans_per_endpoint[endpoint],
                    case_failures=fails_per_case_type[(endpoint, case_type)]
                )
                
                if self.event_callback:
                    self.event_callback("replan_trigger", {
                        "endpoint": endpoint,
                        "case_type": case_type,
                        "failed_mutation": current_scenario.mutation_id,
                        "replan_count": replans_per_endpoint[endpoint]
                    })

                # Dynamic circuit breakers
                if fails_per_case_type[(endpoint, case_type)] >= 2:
                    self.log.error(
                        "D2 Circuit Breaker: dropping case type due to 2 failures",
                        endpoint=endpoint,
                        case_type=case_type
                    )
                    break
                    
                if replans_per_endpoint[endpoint] >= 3:
                    self.log.error(
                        "D2 Circuit Breaker: maximum 3 re-plans reached per endpoint",
                        endpoint=endpoint
                    )
                    break
                    
                # Select next untried mutation of same case type from menu
                endpoint_slice = None
                if self.last_ingest:
                    for ep in self.last_ingest.endpoints:
                        if ep.path == endpoint and ep.method.upper() == current_scenario.method.upper():
                            endpoint_slice = ep
                            break
                            
                next_mutation = None
                if endpoint_slice:
                    tried_ids = {current_scenario.mutation_id}
                    for mut in endpoint_slice.mutations:
                        if mut.case_type == case_type and mut.id not in tried_ids:
                            next_mutation = mut
                            break
                            
                if next_mutation:
                    self.log.info(
                        "D2 feedback: selecting next untried mutation from menu",
                        new_mutation=next_mutation.id
                    )
                    current_scenario = Scenario(
                        endpoint=endpoint,
                        method=current_scenario.method,
                        case_type=case_type,
                        priority=current_scenario.priority,
                        mutation_id=next_mutation.id,
                        expected_status=next_mutation.expected_status
                    )
                    # Advance cursor print dynamically
                    print("")
                    continue
                else:
                    self.log.warning("no alternative mutations available", endpoint=endpoint, case_type=case_type)
                    break
            else:
                break

        pipeline_success = (review is not None and review.status == Status.OK)

        print("================= PIPELINE RESULT =================")
        total_duration = (
            ingest.metadata.duration_ms + plan.metadata.duration_ms +
            generate.metadata.duration_ms + review.metadata.duration_ms
        )
        status_str = "SUCCESS" if pipeline_success else "FAILED"
        print(f"  Status: {status_str}")
        print(f"  Verdicts: {review.verdict.upper()}")
        print(f"  Total Duration: {total_duration}ms")

        # ── E1-5 Cache Stats & Cost/Latency Accounting ────────────────
        cache_stats = get_cache_stats()
        if cache_stats:
            print(f"  Cache — hits: {cache_stats.hits}, misses: {cache_stats.misses}, "
                  f"size: {cache_stats.size}/{cache_stats.max_size}, "
                  f"hit ratio: {cache_stats.hit_ratio:.2%}")
        accounting = get_accounting_report()
        if accounting and accounting.request_count > 0:
            print(f"  Accounting — requests: {accounting.request_count}, "
                  f"total tokens: {accounting.total_tokens}, "
                  f"total latency: {accounting.total_duration_ms}ms, "
                  f"total cost: \${accounting.total_cost:.6f}")
        print("===================================================\n")

        if self.event_callback:
            self.event_callback("pipeline_complete", {
                "success": pipeline_success,
                "total_duration_ms": total_duration
            })

        return pipeline_success



    # ── Optional capability: VISUAL Stage (Track B, ejectable) ─────────────
    def run_visual_stage(self, slices: list[VisualSlice], baseline_dir: str = 'stub/visual_baselines') -> list[VisualReport]:
        """Run the optional VisualStage over a list of VisualSlice inputs.

        Uses the SAME retry-ladder pattern as _execute_stage_with_retry for each slice:
        up to 2 retries on contract errors, then a synthetic FAILED VisualReport
        fallback that records a circuit-breaker failure. Does NOT modify run_pipeline.
        """
        # Import locally so Track A core stays importable when Track B layer is absent.
        from cherenkov.stages.visual.visual_stage import VisualStage

        stage = VisualStage(self.run_id)
        results: list[VisualReport] = []

        for sl in slices:
            attempts = 0
            max_attempts = 3
            report: VisualReport | None = None

            while attempts < max_attempts:
                try:
                    candidate = stage.run(sl, baseline_dir=baseline_dir)
                    if not isinstance(candidate, VisualReport):
                        raise ContractError(f'VisualStage returned unvalidated type for slice {sl.name}')
                    self.log.info('stage success', stage='VISUAL', slice=sl.name, duration_ms=candidate.metadata.duration_ms)
                    report = candidate
                    break
                except (ValidationError, ContractError, Exception) as e:
                    attempts += 1
                    self.log.warning('stage boundary violation', stage='VISUAL', slice=sl.name, attempt=attempts, error=str(e))
                    if attempts >= max_attempts:
                        self.log.error('retry ladder exhausted', stage='VISUAL', slice=sl.name, detail='triggering fallback VisualReport')
                        self.breaker.record_failure()
                        report = VisualReport(
                            scenario_id=sl.name,
                            gates=[],
                            verdict=Verdict.REGENERATE,
                            status=Status.FAILED,
                            errors=[StageError(code='VISUAL_FALLBACK', detail='Failed after retry ladder.')],
                            metadata=StageMeta(stage='VISUAL', duration_ms=0),
                        )
                        break
                    time.sleep(0.1)

            if report is not None:
                results.append(report)

        return results


    # ── Optional capability: PERF Stage (Track B, ejectable) ───────────────
    def run_perf_stage(self, slices, db_path=None):
        """Run the optional PerfStage over a list of PerfSlice inputs.

        Same retry-ladder + circuit-breaker pattern as run_visual_stage. Does
        NOT modify run_pipeline. Returns a list of PerfReport (one per slice).
        """
        from cherenkov.stages.perf.perf_stage import PerfStage
        from cherenkov.core.contracts import PerfReport

        stage = PerfStage(self.run_id, db_path=db_path)
        results = []

        for sl in slices:
            attempts = 0
            max_attempts = 3
            report = None

            while attempts < max_attempts:
                try:
                    candidate = stage.run(sl)
                    if not isinstance(candidate, PerfReport):
                        raise ContractError(f"PerfStage returned unvalidated type for slice {sl.name}")
                    self.log.info("stage success", stage="PERF", slice=sl.name,
                                  duration_ms=candidate.metadata.duration_ms)
                    report = candidate
                    break
                except (ValidationError, ContractError, Exception) as e:
                    attempts += 1
                    self.log.warning("stage boundary violation", stage="PERF",
                                     slice=sl.name, attempt=attempts, error=str(e))
                    if attempts >= max_attempts:
                        self.log.error("retry ladder exhausted", stage="PERF",
                                       slice=sl.name, detail="triggering fallback PerfReport")
                        self.breaker.record_failure()
                        report = PerfReport(
                            scenario_id=sl.name, gates=[], verdict=Verdict.REGENERATE,
                            status=Status.FAILED,
                            errors=[StageError(code="PERF_FALLBACK", detail="Failed after retry ladder.")],
                            metadata=StageMeta(stage="PERF", duration_ms=0),
                        )
                        break
                    time.sleep(0.1)

            if report is not None:
                results.append(report)

        return results
