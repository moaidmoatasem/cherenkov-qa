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
    IngestOutput, PlanOutput, GenerateOutput, ReviewOutput,
    EndpointSlice, Mutation, Scenario, GateResult, Verdict, Status, StageMeta, StageError
)
from cherenkov.core.errors import get_logger, ContractError
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

    def __init__(self, run_id: str | None = None, error_threshold: int = 2):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.log = get_logger("orchestrator", self.run_id)
        self.breaker = CircuitBreaker(threshold=error_threshold)
        self.last_ingest: IngestOutput | None = None

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
    def run_review(self, generate: GenerateOutput, simulate_malformed: bool = False) -> ReviewOutput:
        self.log.info("stage run", stage="REVIEW", scenario_id=generate.scenario_id)
        
        if simulate_malformed:
            return {
                "scenario_id": generate.scenario_id,
                "gates": [],
                "quality_score": 0.0
            } # type: ignore

        return ReviewStage(self.run_id).run(generate)

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
    def run_pipeline(self, spec_path: str, simulate_fail_stage: str | None = None) -> bool:
        """Runs E2E pipeline, tracking progress on the CLI. Returns True on success."""
        # Dynamic GPU/CPU device detection health check at startup
        Config.detect_ollama_device(self.run_id)
        
        print(f"\n================ CHERENKOV PIPELINE RUN [{self.run_id}] ================")
        print("  INGEST  [ Waiting... ]")
        print("  PLAN    [ Waiting... ]")
        print("  GENERATE[ Waiting... ]")
        print("  REVIEW  [ Waiting... ]")
        print("========================================================\n")
        
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

        # Circuit Breaker check
        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            return False

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

        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            return False

        # 3. GENERATE (Runs on the first scenario generated from PLAN)
        if not plan.scenarios:
            self.log.warning("no scenarios available", stage="PLAN")
            print("  GENERATE[ SKIPPED ]")
            print("  REVIEW  [ SKIPPED ]")
            return True

        scenario = plan.scenarios[0]
        print("  GENERATE[ Running... ]")
        generate = self._execute_stage_with_retry(
            "GENERATE",
            lambda: self.run_generate(scenario, simulate_malformed=(simulate_fail_stage == "GENERATE")),
            lambda: GenerateOutput(
                scenario_id=scenario.mutation_id or "unknown",
                test_code="",
                imports=[],
                status=Status.FAILED,
                errors=[StageError(code="GENERATE_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage="GENERATE", duration_ms=0)
            )
        )
        print(f"\033[F  GENERATE[ {generate.status.upper()} ] ({generate.metadata.duration_ms}ms)")

        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            print(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            return False

        # 4. REVIEW
        print("  REVIEW  [ Running... ]")
        review = self._execute_stage_with_retry(
            "REVIEW",
            lambda: self.run_review(generate, simulate_malformed=(simulate_fail_stage == "REVIEW")),
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
        print(f"\033[F  REVIEW  [ {review.status.upper()} ] ({review.metadata.duration_ms}ms)\n")

        print("================= PIPELINE RESULT =================")
        total_duration = (
            ingest.metadata.duration_ms + plan.metadata.duration_ms + 
            generate.metadata.duration_ms + review.metadata.duration_ms
        )
        status_str = "SUCCESS" if review.status == Status.OK else "FAILED"
        print(f"  Status: {status_str}")
        print(f"  Verdicts: {review.verdict.upper()}")
        print(f"  Total Duration: {total_duration}ms")
        print("===================================================\n")
        return review.status == Status.OK
