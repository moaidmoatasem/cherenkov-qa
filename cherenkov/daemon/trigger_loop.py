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
        logger.info(f"[{run_id}] Triggering validation loop for event: {event_context}")

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
            else:
                logger.error(f"[{run_id}] Unsupported source type {self.source_type}")
                return

            logger.info(f"[{run_id}] Planned {len(scenarios)} scenarios.")
            for sc in scenarios:
                GenerateStage("daemon_validate").run(
                    scenario=sc, source_type=self.source_type
                )

            # 2. Invoke the Validation Engine
            from cherenkov.execution.validate import ValidationEngine

            engine = ValidationEngine("daemon_validate")
            logger.info(f"[{run_id}] Running validation against {self.target_url}")
            results = engine.validate_suite(self.target_url, workers=1)

            # 3. Handle failures and Enforce D7 Invariant (Suggest-Only Healing)
            failed_reports = [
                r for r in results.get("reports", []) if not r.get("passed", False)
            ]
            if failed_reports:
                logger.warning(
                    f"[{run_id}] {len(failed_reports)} divergences detected!"
                )
                for report in failed_reports:
                    logger.warning(
                        f"[{run_id}] Divergence in {report.get('scenario_id')}: {report.get('error')}"
                    )
                # We do NOT auto-commit fixes.
                logger.info(
                    f"[{run_id}] Enforcing D7 Invariant: Pushing to HITL Queue instead of auto-merging."
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
                    f"[{run_id}] Validation loop completed successfully. No divergences."
                )

        except Exception as e:
            logger.error(f"[{run_id}] Guardian Validation failed: {e}")
