"""cherenkov/stages/repair.py — ChatTester-style repair loop.

Implements the generate→review→repair cycle from Yuan et al. FSE 2024.
Feeds failing gate details back into a new GenerateStage prompt, repeating
up to max_attempts times. Raises compile rate from ~39% to ~73%.
"""
from __future__ import annotations

from typing import Any, Optional

from cherenkov.core.contracts import GenerateOutput, Status
from cherenkov.core.errors import get_logger
from cherenkov.stages.generate import GenerateStage
from cherenkov.stages.review import ReviewStage

_MAX_ATTEMPTS = 3


class RepairLoop:
    """Generate → Review → (Repair → Review)* bounded loop.

    On each non-auto_approve review, extracts the first failing gate's detail
    and rebuilds the instruction with targeted feedback before re-generating.
    Returns the attempt with the highest quality_score.
    """

    def __init__(self, run_id: str, max_attempts: int = _MAX_ATTEMPTS):
        self.run_id = run_id
        self.max_attempts = max_attempts
        self.log = get_logger("REPAIR", run_id)

    def run(
        self,
        scenario: Any,
        path: str = "",
        method: str = "",
        operation: Optional[dict[str, Any]] = None,
        schemas: Optional[dict[str, Any]] = None,
        instruction: str = "",
        source_type: str = "openapi",
        spec_path: Optional[str] = None,
    ) -> tuple[GenerateOutput, Any]:
        """Run the generate-review-repair loop.

        Returns (best_generate_output, best_review_result).
        best_review_result is None when spec_path is not provided.
        """
        best_generate: Optional[GenerateOutput] = None
        best_review = None
        best_score: float = -1.0
        current_instruction = instruction

        for attempt in range(1, self.max_attempts + 1):
            gen_stage = GenerateStage(run_id=f"{self.run_id}-a{attempt}")
            gen_out = gen_stage.run(
                scenario=scenario,
                path=path,
                method=method,
                operation=operation,
                schemas=schemas,
                instruction=current_instruction,
                source_type=source_type,
            )

            if gen_out.status == Status.FAILED or not gen_out.test_code.strip():
                self.log.warning("generation failed", attempt=attempt)
                break

            if spec_path:
                rev_stage = ReviewStage(run_id=f"{self.run_id}-r{attempt}")
                review = rev_stage.run(gen_out, spec_path=spec_path)
                score = getattr(review, "quality_score", 0.0)
            else:
                review = None
                score = 0.5  # No review; assume neutral score so we keep this attempt

            if score > best_score:
                best_score = score
                best_generate = gen_out
                best_review = review

            if review is None:
                break

            verdict = getattr(review, "verdict", None)
            if verdict and verdict.value == "auto_approve":
                self.log.info("auto_approve reached", attempt=attempt)
                break

            feedback = _extract_error_feedback(review)
            if not feedback:
                self.log.info("no actionable feedback; stopping repair", attempt=attempt)
                break

            # Keep feedback under 300 chars so _sanitize_prompt_input doesn't truncate the critical rules
            feedback_short = feedback[:280]
            current_instruction = (
                f"REPAIR {attempt}: Previous test failed quality gate — {feedback_short}. "
                f"Fix it: use .toBe(NNN) for status, .toHaveProperty() for body shape."
            )
            self.log.info("repair instruction set", attempt=attempt, feedback=feedback_short)

        if best_generate is None:
            # All attempts produced empty output; do one plain generation as fallback
            gen_stage = GenerateStage(run_id=f"{self.run_id}-fallback")
            best_generate = gen_stage.run(
                scenario=scenario,
                path=path,
                method=method,
                operation=operation,
                schemas=schemas,
                instruction=instruction,
                source_type=source_type,
            )

        return best_generate, best_review


def _extract_error_feedback(review) -> str:
    """Return a short description of the first failing gate."""
    for gate in review.gates:
        if not gate.passed and not getattr(gate, "skipped", False):
            gate_name = getattr(gate, "gate", "unknown")
            detail = getattr(gate, "detail", "") or ""
            if detail:
                return f"gate '{gate_name}': {detail}"
            return f"gate '{gate_name}' failed"
    return ""
