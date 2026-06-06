"""
CHERENKOV stages/diagnostics_stage.py — AI Root-Cause Diagnostics Synthesis Stage.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import json
import time
from pydantic import BaseModel, Field

from cherenkov.core.contracts import Status, StageMeta, StageError
from cherenkov.core.config import Config
from cherenkov.core.errors import get_logger
from cherenkov.ai.rag_index import RAGIndex
from cherenkov.ai.ollama_client import complete_json

class DiagnosticsOutput(BaseModel):
    scenario_id: str
    failure_class: str
    error_message: str
    suggested_hypothesis: str
    resolution_steps: list[str] = Field(default_factory=list)
    similar_cases_found: int = 0
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta

SYSTEM_PROMPT = """You are an expert systems reliability engineer and QA architect. Your job is to analyze current test failures, correlate them with similar past incidents, and formulate a high-fidelity root-cause hypothesis and resolution steps.

STRICT RULES:
- Output your analysis ONLY in valid JSON format.
- Output ONLY the JSON block. Do NOT write explanations, prose, or markdown fences.
- Provide a clear, actionable hypothesis and concrete, step-by-step resolution actions.
"""

class DiagnosticsStage:
    """Uses local RAG indexing and Ollama to synthesize failure events and formulate root-cause hypotheses."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("DIAGNOSTICS_STAGE", run_id)
        self.rag = RAGIndex(run_id)

    def _build_user_prompt(
        self,
        scenario_id: str,
        failure_class: str,
        error_message: str,
        similar_incidents: list[dict]
    ) -> str:
        """Constructs the RAG-augmented synthesis prompt."""
        return (
            "CURRENT TEST FAILURE:\n"
            + f"  Scenario ID: {scenario_id}\n"
            + f"  Failure Class: {failure_class}\n"
            + f"  Error Message: {error_message}\n\n"
            + "PAST SIMILAR INCIDENTS RETRIEVED FROM RAG:\n"
            + json.dumps(similar_incidents, indent=2)
            + "\n\nFormulate a root-cause hypothesis and resolution steps. "
            + "Return a JSON object with keys: 'suggested_hypothesis' (string) and 'resolution_steps' (array of strings)."
        )

    def run(
        self,
        scenario_id: str,
        failure_class: str,
        error_message: str
    ) -> DiagnosticsOutput:
        t0 = time.time()
        self.log.info("stage start", scenario_id=scenario_id, failure_class=failure_class)

        # 1. Query RAG vector database for similar past occurrences
        similar_incidents = self.rag.query_similar_incidents(error_message, limit=2)
        self.log.info("retrieved similar RAG incidents", count=len(similar_incidents))

        user_prompt = self._build_user_prompt(scenario_id, failure_class, error_message, similar_incidents)

        suggested_hypothesis = ""
        resolution_steps = []
        errors = []

        try:
            # 2. Invoke local model to synthesize root-cause analysis
            parsed = complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=Config.GEN_MODEL,
                run_id=self.run_id
            )
            suggested_hypothesis = parsed.get("suggested_hypothesis", parsed.get("hypothesis", "Could not formulate definitive hypothesis."))
            resolution_steps = parsed.get("resolution_steps", [])
            self.log.info("successfully synthesized root-cause hypothesis")
        except Exception as e:
            # Resilient fallback: return local heuristic diagnostic if model is offline or returns malformed JSON
            self.log.warning("Ollama synthesis failed, using local fallback heuristics", error=str(e))
            suggested_hypothesis = f"SUGGESTION: Suspected {failure_class} incident based on test failure stack."
            resolution_steps = [
                "Verify target API endpoint configuration.",
                "Review recent database schema change logs.",
                "Ensure client authentication credential baseline is up-to-date."
            ]
            errors.append(StageError(code="DIAGNOSTICS_SYNTHESIS_FAILED", detail=str(e)))

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", duration_ms=dt)

        return DiagnosticsOutput(
            scenario_id=scenario_id,
            failure_class=failure_class,
            error_message=error_message,
            suggested_hypothesis=suggested_hypothesis,
            resolution_steps=resolution_steps,
            similar_cases_found=len(similar_incidents),
            status=Status.OK if not errors else Status.DEGRADED,
            errors=errors,
            metadata=StageMeta(stage="DIAGNOSTICS_STAGE", duration_ms=dt)
        )
