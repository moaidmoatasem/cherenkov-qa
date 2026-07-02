"""
Spec Guardian Trigger Loop (Horizon 3)
Orchestrates test generation and validation upon drift detection.
"""

import logging
import time

logger = logging.getLogger(__name__)


class SpecGuardianTriggerLoop:
    """
    Executes the D7-compliant validation pipeline autonomously.
    """

    def __init__(self, target_url: str, source_type: str = "openapi"):
        self.active_runs = {}
        self.target_url = target_url
        self.source_type = source_type

    def trigger_validation(self, event_context: dict):
        """
        Invokes test generation based on a detected change event.
        Ensures execution adheres to 'Suggest-Only Healing' invariants.
        """
        run_id = event_context.get("id", f"drift_{int(time.time())}")
        spec_path = event_context.get("file_path", "openapi.yaml")
        logger.info("[%s] Triggering validation loop for event: %s", run_id, event_context)

        try:
            # 1. Fetch the delta/spec changes and invoke the generative pipeline
            from cherenkov.stages.generate import GenerateStage

            if self.source_type == "openapi":
                from cherenkov.stages.ingest import IngestStage
                from cherenkov.stages.plan import PlanStage

                ingest_output = IngestStage("daemon_validate").run(spec_path)
                plan_output = PlanStage("daemon_validate").run(ingest_output)
                scenarios = plan_output.scenarios
            elif self.source_type == "graphql":
                from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
                from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner

                source = GraphQLSourceAdapter(spec_path)
                planner = GraphQLScenarioPlanner()
                scenarios = planner.plan(source)
            elif self.source_type == "grpc":
                from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
                from cherenkov.stages.plan_grpc import gRPCScenarioPlanner

                source = gRPCSourceAdapter(spec_path)
                planner = gRPCScenarioPlanner()
                scenarios = planner.plan(source)
            elif self.source_type == "accessibility":
                from cherenkov.sources.accessibility.adapter import AccessibilitySourceAdapter
                from cherenkov.stages.plan_accessibility import AccessibilityScenarioPlanner

                source = AccessibilitySourceAdapter(spec_path)
                planner = AccessibilityScenarioPlanner()
                scenarios = planner.plan(source)
            else:
                logger.error("[%s] Unsupported source type %s", run_id, self.source_type)
                return

            logger.info("[%s] Planned %d scenarios.", run_id, len(scenarios))
            for sc in scenarios:
                GenerateStage("daemon_validate").run(
                    scenario=sc, source_type=self.source_type
                )

            # 2. Invoke the Validation Engine
            from cherenkov.execution.validate import ValidationEngine

            engine = ValidationEngine("daemon_validate")
            logger.info("[%s] Running validation against %s", run_id, self.target_url)
            results = engine.validate_suite(self.target_url, workers=1)

            # 3. Handle failures and Enforce D7 Invariant (Suggest-Only Healing)
            failed_reports = [
                r for r in results.get("reports", []) if not r.get("passed", False)
            ]
            if failed_reports:
                logger.warning("[%s] %d divergences detected!", run_id, len(failed_reports))
                for report in failed_reports:
                    logger.warning(
                        "[%s] Divergence in %s: %s",
                        run_id,
                        report.get("scenario_id"),
                        report.get("error"),
                    )
                # We do NOT auto-commit fixes.
                logger.info(
                    "[%s] Enforcing D7 Invariant: Pushing to HITL Queue instead of auto-merging.",
                    run_id,
                )

                # Push to HITL queue
                from cherenkov.hitl.queue import HitlQueue
                from cherenkov.core.contracts import DivergenceFinding

                queue = HitlQueue()
                for report in failed_reports:
                    finding = DivergenceFinding(
                        violation_type="conformance-drift",
                        endpoint=report.get("scenario_id", "unknown"),
                        http_method="ANY",
                        expected="Valid response",
                        actual=report.get("error", "Error"),
                        summary="Response drift detected by Spec Guardian",
                        description=report.get("error", "Error"),
                        severity="high",
                        remediation="Update API or spec",
                    )
                    queue.push_finding(finding, run_id=run_id)
            else:
                logger.info(
                    "[%s] Validation loop completed successfully. No divergences.", run_id
                )

        except Exception as e:
            logger.error("[%s] Guardian Validation failed: %s", run_id, e)
