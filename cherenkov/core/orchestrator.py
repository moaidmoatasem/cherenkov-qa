from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from cherenkov.ai import get_accounting_report, get_cache_stats
from cherenkov.core.contracts import (
    EndpointSlice,
    GenerateOutput,
    IngestOutput,
    PlanOutput,
    ReviewOutput,
    Scenario,
    StageError,
    StageMeta,
    Status,
    Verdict,
    VisualReport,
    VisualSlice,
)
from cherenkov.core.d2_controller import D2FeedbackController
from cherenkov.core.errors import get_logger, set_events_file
from cherenkov.core.settings import get_settings
from cherenkov.core.stage_executor import CircuitBreaker, StageExecutor
from cherenkov.stages.generate import GenerateStage
from cherenkov.stages.ingest import IngestStage
from cherenkov.stages.plan import PlanStage
from cherenkov.stages.review import ReviewStage


class OrchestrationEngine:
    """Central execution engine orchestrating stages E2E."""

    def __init__(
        self,
        run_id: str | None = None,
        error_threshold: int = 2,
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.run_id = run_id or str(uuid.uuid4())[:8]

        run_dir = os.path.abspath(f".cherenkov/runs/{self.run_id}")
        os.makedirs(run_dir, exist_ok=True)
        self._events_file = open(  # noqa: SIM115 — kept open for pipeline duration
            os.path.join(run_dir, "events.jsonl"), "a", encoding="utf-8"
        )
        set_events_file(self._events_file)

        self.log = get_logger("orchestrator", self.run_id)
        self.breaker = CircuitBreaker(threshold=error_threshold)
        self.executor = StageExecutor(self.breaker, self.log)
        self.last_ingest: IngestOutput | None = None
        self.event_callback = event_callback

    def close(self):
        set_events_file(None)
        if self._events_file and not self._events_file.closed:
            self._events_file.close()
            self._events_file = None

    def _progress(self, *args, **kwargs) -> None:
        print(*args, **kwargs)

    def _emit_event(self, event: str, data: dict) -> None:
        if self.event_callback:
            try:
                self.event_callback(event, data)
            except Exception as cb_err:
                self.log.warning("event_callback_failed", error=str(cb_err))

    # ── Stage 1: INGEST ────────────────────────────────────────────
    def run_ingest(
        self, spec_path: str, simulate_malformed: bool = False
    ) -> IngestOutput:
        self.log.info("stage run", stage="INGEST", spec_path=spec_path)
        if simulate_malformed:
            assert (
                os.getenv("CHERENKOV_ENV", "production") != "production"
            ), "Simulation flags are not allowed in production. Set CHERENKOV_ENV=development to enable."
            return {"endpoints": [], "client_stub_path": "stub/client.ts"}  # type: ignore
        ingest_output = IngestStage(self.run_id).run(spec_path)
        self.last_ingest = ingest_output
        return ingest_output

    # ── Stage 2: PLAN ──────────────────────────────────────────────
    def run_plan(
        self, ingest: IngestOutput, simulate_malformed: bool = False
    ) -> PlanOutput:
        self.log.info("stage run", stage="PLAN", endpoints_count=len(ingest.endpoints))
        if simulate_malformed:
            assert (
                os.getenv("CHERENKOV_ENV", "production") != "production"
            ), "Simulation flags are not allowed in production. Set CHERENKOV_ENV=development to enable."
            return {"scenarios": []}  # type: ignore
        return PlanStage(self.run_id).run(ingest)

    # ── Stage 3: GENERATE ──────────────────────────────────────────
    def run_generate(
        self, scenario: Scenario, simulate_malformed: bool = False
    ) -> GenerateOutput:
        self.log.info("stage run", stage="GENERATE", scenario_id=scenario.mutation_id)
        if simulate_malformed:
            assert (
                os.getenv("CHERENKOV_ENV", "production") != "production"
            ), "Simulation flags are not allowed in production. Set CHERENKOV_ENV=development to enable."
            return {"scenario_id": scenario.mutation_id or "unknown", "test_code": ""}  # type: ignore

        endpoint_slice = None
        if self.last_ingest:
            for ep in self.last_ingest.endpoints:
                if (
                    ep.path == scenario.endpoint
                    and ep.method.upper() == scenario.method.upper()
                ):
                    endpoint_slice = ep
                    break

        if not endpoint_slice:
            endpoint_slice = EndpointSlice(
                path=scenario.endpoint, method=scenario.method,
                operation={}, schemas={}, richness=0.5, mutations=[],
            )

        instruction = "Provide valid request payload."
        for mut in endpoint_slice.mutations:
            if mut.id == scenario.mutation_id:
                instruction = mut.instruction
                break

        return GenerateStage(self.run_id).run(
            scenario=scenario, path=endpoint_slice.path, method=endpoint_slice.method,
            operation=endpoint_slice.operation, schemas=endpoint_slice.schemas,
            instruction=instruction,
        )

    # ── Stage 4: REVIEW ────────────────────────────────────────────
    def run_review(
        self, generate: GenerateOutput, spec_path: str, simulate_malformed: bool = False
    ) -> ReviewOutput:
        self.log.info("stage run", stage="REVIEW", scenario_id=generate.scenario_id)
        if simulate_malformed:
            assert (
                os.getenv("CHERENKOV_ENV", "production") != "production"
            ), "Simulation flags are not allowed in production. Set CHERENKOV_ENV=development to enable."
            return {
                "scenario_id": generate.scenario_id,
                "gates": [], "quality_score": 0.0,
            }  # type: ignore
        return ReviewStage(self.run_id).run(generate, spec_path)

    # ── Backward-compat: delegate to StageExecutor ────────────────
    def _execute_stage_with_retry(
        self,
        stage_name: str,
        stage_func: Callable[[], Any],
        fallback_factory: Callable[[], Any],
    ) -> Any:
        return self.executor.execute(stage_name, stage_func, fallback_factory)

    # ── Per-scenario GENERATE+REVIEW worker ────────────────────────
    def _run_scenario(
        self,
        scenario: Scenario,
        spec_path: str,
        simulate_fail_stage: str | None,
    ) -> tuple[bool, int, int]:
        set_events_file(self._events_file)

        d2 = D2FeedbackController(last_ingest=self.last_ingest)
        current_scenario = scenario
        generate: GenerateOutput | None = None
        review: ReviewOutput | None = None

        self._emit_event("stage_start", {"stage": "GENERATE", "scenario": scenario.mutation_id})

        while True:
            if self.breaker.tripped:
                return False, 0, 0

            generate = self.executor.execute(
                "GENERATE",
                lambda cs=current_scenario: self.run_generate(
                    cs, simulate_malformed=(simulate_fail_stage == "GENERATE")
                ),
                lambda cs=current_scenario: GenerateOutput(
                    scenario_id=cs.mutation_id or "unknown",
                    test_code="", imports=[],
                    status=Status.FAILED,
                    errors=[StageError(code="GENERATE_FALLBACK", detail="Failed after retry ladder.")],
                    metadata=StageMeta(stage="GENERATE", duration_ms=0),
                ),
            )

            if generate.status == Status.OK:
                self._emit_event("test_generated", {
                    "endpoint": current_scenario.endpoint,
                    "method": current_scenario.method,
                    "code": generate.test_code,
                    "agent": get_settings().GEN_MODEL,
                })

            if self.breaker.tripped:
                return False, generate.metadata.duration_ms, 0

            if generate.status != Status.OK:
                self.log.warning("skipping REVIEW: generate stage failed", scenario_id=generate.scenario_id)
                self._emit_event("stage_skip", {"stage": "REVIEW", "reason": "generate failed"})
                return False, generate.metadata.duration_ms, 0

            self._emit_event("stage_start", {"stage": "REVIEW"})

            review = self.executor.execute(
                "REVIEW",
                lambda g=generate: self.run_review(
                    g, spec_path, simulate_malformed=(simulate_fail_stage == "REVIEW")
                ),
                lambda g=generate: ReviewOutput(
                    scenario_id=g.scenario_id, gates=[], quality_score=0.0,
                    verdict=Verdict.REGENERATE, status=Status.FAILED,
                    errors=[StageError(code="REVIEW_FALLBACK", detail="Failed after retry ladder.")],
                    metadata=StageMeta(stage="REVIEW", duration_ms=0),
                ),
            )

            self._emit_event("stage_success", {
                "stage": "REVIEW",
                "summary": f"Review complete with verdict: {review.verdict.value.upper()}",
                "duration_ms": review.metadata.duration_ms,
            })

            if self.breaker.tripped:
                return (review.status == Status.OK), generate.metadata.duration_ms, review.metadata.duration_ms

            # D2 Planner Feedback loop
            prism_failed = any(
                g.gate == "prism-dryrun" and not g.passed for g in review.gates
            )
            if prism_failed:
                endpoint = current_scenario.endpoint
                case_type = current_scenario.case_type
                d2.record_failure(endpoint, case_type)

                self.log.warning(
                    "D2 Planner Feedback loop triggered due to Prism dry-run failure",
                    endpoint=endpoint, case_type=case_type,
                    failed_mutation=current_scenario.mutation_id,
                    replan_count=d2.replans_per_endpoint[endpoint],
                    case_failures=d2.fails_per_case_type[(endpoint, case_type)],
                )
                self._emit_event("replan_trigger", {
                    "endpoint": endpoint, "case_type": case_type,
                    "failed_mutation": current_scenario.mutation_id,
                    "replan_count": d2.replans_per_endpoint[endpoint],
                })

                if not d2.should_retry(endpoint, case_type):
                    break

                next_scenario = d2.get_next_mutation(current_scenario, case_type)
                if next_scenario:
                    current_scenario = next_scenario
                    continue
                break
            break

        ok = review is not None and review.status == Status.OK
        gen_ms = generate.metadata.duration_ms if generate else 0
        rev_ms = review.metadata.duration_ms if review else 0
        return ok, gen_ms, rev_ms

    # ── Pipeline stage helpers ─────────────────────────────────────
    def _run_ingest_stage(self, spec_path: str, simulate_fail_stage: str | None) -> IngestOutput:
        self._emit_event("stage_start", {"stage": "INGEST"})
        self._progress("  INGEST  [ Running... ]")
        ingest = self.executor.execute(
            "INGEST",
            lambda: self.run_ingest(spec_path, simulate_malformed=(simulate_fail_stage == "INGEST")),
            lambda: IngestOutput(
                endpoints=[], client_stub_path="stub/client.ts", status=Status.FAILED,
                errors=[StageError(code="INGEST_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage="INGEST", duration_ms=0),
            ),
        )
        self._progress(f"  INGEST  [ {ingest.status.value.upper()} ] ({ingest.metadata.duration_ms}ms")
        self._emit_event("stage_success", {
            "stage": "INGEST",
            "summary": f"{len(ingest.endpoints)} endpoints indexed",
            "duration_ms": ingest.metadata.duration_ms,
        })
        return ingest

    def _run_plan_stage(self, ingest: IngestOutput, simulate_fail_stage: str | None) -> PlanOutput:
        self._emit_event("stage_start", {"stage": "PLAN"})
        self._progress("  PLAN    [ Running... ]")
        plan = self.executor.execute(
            "PLAN",
            lambda: self.run_plan(ingest, simulate_malformed=(simulate_fail_stage == "PLAN")),
            lambda: PlanOutput(
                scenarios=[], status=Status.FAILED,
                errors=[StageError(code="PLAN_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage="PLAN", duration_ms=0),
            ),
        )
        self._progress(f"  PLAN    [ {plan.status.value.upper()} ] ({plan.metadata.duration_ms}ms")
        self._emit_event("stage_success", {
            "stage": "PLAN",
            "summary": f"{len(plan.scenarios)} scenarios planned",
            "duration_ms": plan.metadata.duration_ms,
        })
        return plan

    def _run_scenarios_phase(
        self, plan: PlanOutput, spec_path: str, simulate_fail_stage: str | None
    ) -> tuple[bool, list[bool], list[int], set[str], set[str]]:
        if not plan.scenarios:
            self.log.warning("no scenarios available", stage="PLAN")
            self._progress("  GENERATE[ SKIPPED ]")
            self._progress("  REVIEW  [ SKIPPED ]")
            return True, [], [], set(), set()

        max_workers = min(len(plan.scenarios), get_settings().MAX_CONCURRENT_SCENARIOS)
        self._progress(f"  Running {len(plan.scenarios)} scenario(s) [{max_workers} concurrent]...\n")

        scenario_results: list[bool] = []
        all_durations: list[int] = []
        all_endpoints: set[str] = set()
        passed_endpoints: set[str] = set()

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._run_scenario, s, spec_path, simulate_fail_stage): s
                for s in plan.scenarios
            }
            for fut in as_completed(futures):
                s = futures[fut]
                ep_key = f"{s.method.upper()} {s.endpoint}"
                all_endpoints.add(ep_key)
                try:
                    ok, gen_ms, rev_ms = fut.result()
                except Exception as exc:
                    self.log.error("scenario_thread_error", error=str(exc), scenario=getattr(s, "mutation_id", "?"))
                    ok, gen_ms, rev_ms = False, 0, 0

                if ok:
                    passed_endpoints.add(ep_key)
                scenario_results.append(ok)
                all_durations.extend(ms for ms in (gen_ms, rev_ms) if ms)
                label = s.mutation_id or f"{s.method} {s.endpoint}"
                self._progress(f"  {'PASS' if ok else 'FAIL'}  {label} (gen {gen_ms}ms, rev {rev_ms}ms)")

                if self.breaker.tripped:
                    self.log.error("pipeline aborted", reason="circuit breaker tripped")
                    self._progress(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
                    for f in futures:
                        f.cancel()
                    return False, scenario_results, all_durations, all_endpoints, passed_endpoints

        pipeline_success = all(scenario_results) if scenario_results else False
        return pipeline_success, scenario_results, all_durations, all_endpoints, passed_endpoints

    def _run_post_generation_evals(self) -> None:
        if os.getenv("CHERENKOV_EVALS_ENABLED", "0") != "1":
            return
        try:
            from pathlib import Path

            from cherenkov.evals.core import EvalSample
            from cherenkov.evals.runner import run_evals
            from cherenkov.evals.store import EvalStore
            from cherenkov.observability.llm_tracer import trace_event

            self.log.info("running post-generation eval judge")
            self._progress("\n  EVALS   [ Running LLM-as-judge... ]")

            output_dir = Path(get_settings().OUTPUT_DIR)
            if not output_dir.exists():
                self._progress("  EVALS   [ SKIPPED ] output directory not found")
                return

            test_files = list(output_dir.glob("*.spec.ts"))
            if not test_files:
                self._progress("  EVALS   [ SKIPPED ] no test files found")
                return

            samples = []
            for test_file in test_files[:10]:
                try:
                    code = test_file.read_text(encoding="utf-8")
                    samples.append(EvalSample(
                        scenario_id=test_file.stem, endpoint="unknown",
                        method="GET", expected_status=200, test_code=code, spec_summary="",
                    ))
                except Exception as e:
                    self.log.warning("failed to read test file", file=str(test_file), error=str(e))

            if not samples:
                self._progress("  EVALS   [ SKIPPED ] no test files found")
                return

            report = run_evals(samples)
            EvalStore().save(report)
            trace_event("pipeline-evals", pass_rate=report.pass_rate(), scenarios=len(samples))
            self._progress(f"  EVALS   [ DONE ] pass_rate={report.pass_rate():.1%}, saved to .cherenkov/evals.db")
            self.log.info("eval judge complete", pass_rate=report.pass_rate(), total=len(samples))
        except Exception as e:
            self.log.warning("post-generation evals failed (non-fatal)", error=str(e))
            self._progress(f"  EVALS   [ SKIPPED ] {e}")

    def _run_adversarial_scan(self) -> None:
        if os.getenv("CHERENKOV_ADVERSARIAL_ENABLED", "0") != "1":
            return
        try:
            from pathlib import Path

            from cherenkov.adversarial.runner import run_adversarial_tests, save_report
            from cherenkov.observability.llm_tracer import trace_event

            self.log.info("running post-generation adversarial scan")
            self._progress("\n  ADVERSARIAL [ Scanning for injection patterns... ]")

            output_dir = Path(get_settings().OUTPUT_DIR)
            if not output_dir.exists():
                self._progress("  ADVERSARIAL [ SKIPPED ] output directory not found")
                return

            test_files = list(output_dir.glob("*.spec.ts"))
            if not test_files:
                self._progress("  ADVERSARIAL [ SKIPPED ] no test files found")
                return

            test_codes = {}
            for test_file in test_files[:20]:
                try:
                    test_codes[test_file.stem] = test_file.read_text(encoding="utf-8")
                except Exception as e:
                    self.log.warning("failed to read test file", file=str(test_file), error=str(e))

            if not test_codes:
                self._progress("  ADVERSARIAL [ SKIPPED ] no test files found")
                return

            report = run_adversarial_tests(test_codes, spec_path=str(output_dir))
            output_path = save_report(report)
            trace_event("pipeline-adversarial", pass_rate=report.pass_rate(), critical=len(report.critical_findings()))

            criticals = report.critical_findings()
            if criticals:
                self._progress(f"  ADVERSARIAL [ WARN ] {len(criticals)} critical findings, saved to {output_path}")
                self.log.warning("adversarial scan found critical issues", count=len(criticals))
            else:
                self._progress(f"  ADVERSARIAL [ PASS ] no critical findings, saved to {output_path}")
                self.log.info("adversarial scan complete", pass_rate=report.pass_rate())
        except Exception as e:
            self.log.warning("post-generation adversarial scan failed (non-fatal)", error=str(e))
            self._progress(f"  ADVERSARIAL [ SKIPPED ] {e}")

    def _report_and_persist(
        self, pipeline_success: bool, scenario_results: list[bool],
        all_durations: list[int], all_endpoints: set[str], passed_endpoints: set[str],
    ) -> None:
        successes = sum(1 for r in scenario_results if r)
        total = len(scenario_results)
        total_duration = sum(all_durations)

        if not pipeline_success:
            self.log.warning("pipeline completed with failures", total=total, passed=successes)

        self._progress("================= PIPELINE RESULT =================")
        status_str = f"PASS ({successes}/{total})" if successes == total else f"FAIL ({successes}/{total} passed)"
        self._progress(f"  Status: {status_str}")
        self._progress(f"  Scenarios: {successes}/{total} passed")
        self._progress(f"  Total Duration: {total_duration}ms")

        cache_stats = get_cache_stats()
        if cache_stats:
            self._progress(f"  Cache - hits: {cache_stats.hits}, misses: {cache_stats.misses}, "
                  f"size: {cache_stats.size}/{cache_stats.max_size}, "
                  f"hit ratio: {cache_stats.hit_ratio:.2%}")
        accounting = get_accounting_report()
        if accounting and accounting.request_count > 0:
            self._progress(f"  Accounting - requests: {accounting.request_count}, "
                  f"total tokens: {accounting.total_tokens}, "
                  f"total latency: {accounting.total_duration_ms}ms, "
                  f"total cost: ${accounting.total_cost:.6f}")
        self._progress("===================================================\n")

        self._emit_event("pipeline_complete", {
            "success": pipeline_success, "total_duration_ms": total_duration,
            "scenarios_passed": successes, "scenarios_total": total,
        })

        try:
            from cherenkov.observability.llm_tracer import trace_event
            trace_event("pipeline-complete", run_id=self.run_id, success=pipeline_success,
                        duration_ms=total_duration, scenarios_passed=successes, scenarios_total=total)
        except Exception:
            pass

        try:
            from cherenkov.governance.gen_metrics import GenMetricsStore, RunGenMetrics
            metrics = RunGenMetrics(run_id=self.run_id)
            for ok in scenario_results:
                metrics.record_generation(all_gates_passed=ok)
            for ep in all_endpoints:
                metrics.record_operation(covered=(ep in passed_endpoints))
            GenMetricsStore().save(metrics)
            self._progress(metrics.render())
        except Exception as me:
            self.log.warning("gen_metrics_save_failed", error=str(me))

        try:
            from cherenkov.core.stats_store import StatsStore
            from cherenkov.reflector.reflector import Reflector
            stats_store = StatsStore()
            rstats = Reflector().get_stats()
            cache_hit = cache_stats.hit_ratio if cache_stats else None
            cost = accounting.total_cost if accounting else 0.0
            stats_store.record_run(
                run_id=self.run_id, success=pipeline_success,
                scenarios_passed=successes, scenarios_total=total,
                total_duration_ms=total_duration, total_cost=cost,
                cache_hit_ratio=cache_hit,
                verdict_count=rstats.get("verdict_count", 0),
                idiom_count=rstats.get("idiom_count", 0),
            )
        except Exception as e:
            self.log.error("stats_persist_failed", error=str(e), run_id=getattr(self, "run_id", "unknown"))

    # ── E2E Orchestration ─────────────────────────────────────────
    def run_pipeline(
        self,
        spec_path: str,
        simulate_fail_stage: str | None = None,
    ) -> bool:
        try:
            return self._run_pipeline_inner(spec_path, simulate_fail_stage)
        finally:
            self.close()

    def _run_pipeline_inner(
        self,
        spec_path: str,
        simulate_fail_stage: str | None = None,
    ) -> bool:
        if simulate_fail_stage:
            assert (
                os.getenv("CHERENKOV_ENV", "production") != "production"
            ), "Simulation flags are not allowed in production. Set CHERENKOV_ENV=development to enable."

        self.breaker.reset()
        get_settings().detect_ollama_device(self.run_id)

        try:
            from cherenkov.observability.llm_tracer import trace_event
            trace_event("pipeline-start", run_id=self.run_id, spec_path=spec_path)
        except Exception:
            pass

        self._progress(f"\n================ CHERENKOV PIPELINE RUN [{self.run_id}] ================")
        self._progress("  INGEST  [ Waiting... ]")
        self._progress("  PLAN    [ Waiting... ]")
        self._progress("  GENERATE[ Waiting... ]")
        self._progress("  REVIEW  [ Waiting... ]")
        self._progress("========================================================\n")

        ingest = self._run_ingest_stage(spec_path, simulate_fail_stage)

        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            self._progress(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            self._emit_event("pipeline_complete", {"success": False, "reason": "Circuit breaker tripped"})
            return False

        plan = self._run_plan_stage(ingest, simulate_fail_stage)

        if self.breaker.tripped:
            self.log.error("pipeline aborted", reason="circuit breaker tripped")
            self._progress(f"\n  ABORTED: Circuit breaker tripped ({self.breaker.error_count} failures).\n")
            self._emit_event("pipeline_complete", {"success": False, "reason": "Circuit breaker tripped"})
            return False

        pipeline_success, scenario_results, all_durations, all_endpoints, passed_endpoints = \
            self._run_scenarios_phase(plan, spec_path, simulate_fail_stage)

        all_durations.insert(0, ingest.metadata.duration_ms)
        all_durations.insert(1, plan.metadata.duration_ms)

        self._run_post_generation_evals()
        self._run_adversarial_scan()
        self._report_and_persist(pipeline_success, scenario_results, all_durations, all_endpoints, passed_endpoints)

        return pipeline_success

    # ── Optional: VISUAL Stage ─────────────────────────────────────
    def run_visual_stage(
        self, slices: list[VisualSlice], baseline_dir: str = "stub/visual_baselines"
    ) -> list[VisualReport]:
        from cherenkov.stages.visual.visual_stage import VisualStage

        return self.executor.execute_with_vlm_retry(
            stage_name="VISUAL",
            slices=slices,
            stage_factory=lambda: VisualStage(self.run_id),
            run_slice=lambda stage, sl: stage.run(sl, baseline_dir=baseline_dir),
            fallback_report_factory=lambda slice_name, stage: VisualReport(
                scenario_id=slice_name,
                gates=[], verdict=Verdict.REGENERATE,
                status=Status.FAILED,
                errors=[StageError(code=f"{stage}_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage=stage, duration_ms=0),
            ),
            report_type=VisualReport,
            contract_error_msg="VisualStage returned unvalidated type for slice {slice_name}",
        )

    # ── Optional: PERF Stage ───────────────────────────────────────
    def run_perf_stage(self, slices, db_path=None):
        from cherenkov.core.contracts import PerfReport
        from cherenkov.stages.perf.perf_stage import PerfStage

        return self.executor.execute_with_vlm_retry(
            stage_name="PERF",
            slices=slices,
            stage_factory=lambda: PerfStage(self.run_id, db_path=db_path),
            run_slice=lambda stage, sl: stage.run(sl),
            fallback_report_factory=lambda slice_name, stage: PerfReport(
                scenario_id=slice_name,
                gates=[], verdict=Verdict.REGENERATE,
                status=Status.FAILED,
                errors=[StageError(code=f"{stage}_FALLBACK", detail="Failed after retry ladder.")],
                metadata=StageMeta(stage=stage, duration_ms=0),
            ),
            report_type=PerfReport,
            contract_error_msg="PerfStage returned unvalidated type for slice {slice_name}",
        )


# Backward-compatible re-exports
