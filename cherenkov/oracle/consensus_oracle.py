"""
CHERENKOV oracle/consensus_oracle.py — CANDOR-inspired multi-agent consensus oracle.

Runs 2-4 independent LLM evaluation passes to determine whether the assertions
in a generated test correctly verify the expected endpoint behavior. A verdict
is accepted only when a configurable majority of passes agree.

Research basis: CANDOR ("Hallucination to Consensus", arXiv 2506.02943)
achieved >= 15.8 percentage-point gains over prior SOTA on oracle correctness
by running a "panel discussion" of LLM agents and requiring consensus before
accepting an assertion. Key insight: individual LLM passes hallucinate
assertions; majority voting cancels out single-pass errors.

Design:
  - Uses the existing Ollama substrate — no new model dependencies.
  - Each pass is a compact JSON-mode call (low latency) on the same model.
  - Passes use slightly increasing temperatures (0.05, 0.10, 0.15) to obtain
    independent samples rather than deterministic repeats.
  - Configurable: passes=2 for speed, passes=3 for balanced quality (default).
  - Fallback: if all passes error, returns is_correct=False with low confidence
    rather than raising, keeping the pipeline non-blocking.
"""

from __future__ import annotations

from typing import Any

from cherenkov.core.contracts import Claim
from cherenkov.core.errors import get_logger
from cherenkov.oracle.interface import Oracle, OracleResult


_EVAL_SYSTEM_PROMPT = (
    "You are an expert test oracle evaluator. Given a Playwright TypeScript "
    "test and the OpenAPI operation it targets, determine whether the "
    "assertions in the test correctly and meaningfully verify the endpoint's "
    "expected behavior.\n\n"
    "Respond ONLY with valid JSON matching exactly this schema:\n"
    '{"verdict": "correct" | "incorrect", "confidence": 0.0-1.0, "reason": "..."}\n\n'
    'verdict: "correct" if the assertions test the right status codes and '
    'response shapes; "incorrect" if they are missing, wrong, or vacuous.\n'
    "confidence: how certain you are (0.0 = pure guess, 1.0 = certain).\n"
    "reason: one concise sentence."
)


class ConsensusOracle(Oracle):
    """
    Multi-pass LLM oracle implementing the CANDOR consensus pattern.

    Runs N independent LLM evaluations and returns the majority verdict.
    Confidence is the product of the per-pass average confidence and the
    agreement ratio, so unanimous agreement at high confidence scores highest.

    Integrates with the Oracle SPI (oracle/interface.py) so it can be
    dropped in wherever an Oracle is accepted.
    """

    def __init__(
        self,
        passes: int = 3,
        consensus_threshold: float = 0.6,
        run_id: str | None = None,
    ) -> None:
        """
        Args:
            passes: Number of independent LLM evaluation passes (2-4).
                    More passes increase reliability but cost more inference time.
            consensus_threshold: Fraction of passes that must agree for the
                    oracle to return is_correct=True (e.g. 0.6 means at least
                    ceil(0.6 * passes) must agree). 0.5 = simple majority.
            run_id: Optional run identifier forwarded to the structured logger.
        """
        self.passes = max(2, min(passes, 4))
        self.consensus_threshold = consensus_threshold
        self.log = get_logger("CONSENSUS_ORACLE", run_id)

    def evaluate(self, claim: Claim, **kwargs: Any) -> OracleResult:
        """
        Evaluate whether the test assertions in the claim are correct.

        Expected kwargs:
            test_code (str): Generated Playwright TypeScript test to evaluate.
            endpoint_slice (dict): Keys: path, method, operation, schemas.
                The operation dict should include the "responses" key so the
                oracle can check expected status codes.

        Returns:
            OracleResult where:
              - is_correct=True iff >= consensus_threshold fraction of passes agree.
              - confidence = avg_confidence_across_passes * agreement_ratio.
              - detail summarises the vote and a sample reason.
        """
        test_code: str = kwargs.get("test_code", "")
        endpoint_slice: dict = kwargs.get("endpoint_slice", {})

        if not test_code.strip():
            return OracleResult(
                is_correct=False,
                confidence=0.0,
                detail="ConsensusOracle: no test code provided.",
            )

        verdicts: list[bool] = []
        confidences: list[float] = []
        reasons: list[str] = []

        for i in range(self.passes):
            result = self._single_pass(test_code, endpoint_slice, pass_num=i)
            verdicts.append(result["verdict"] == "correct")
            confidences.append(float(result["confidence"]))
            reasons.append(str(result["reason"]))

        agree_count = sum(verdicts)
        agree_ratio = agree_count / len(verdicts)
        is_correct = agree_ratio >= self.consensus_threshold
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        combined_confidence = round(avg_confidence * agree_ratio, 4)

        sample_reasons = " | ".join(r for r in reasons[:2] if r)
        detail = (
            f"Consensus: {agree_count}/{self.passes} agree "
            f"(threshold {self.consensus_threshold:.0%}). "
            + (f"Reasons: {sample_reasons}" if sample_reasons else "")
        )

        self.log.info(
            "consensus verdict",
            claim_id=claim.id,
            is_correct=is_correct,
            agree_ratio=round(agree_ratio, 3),
            avg_confidence=round(avg_confidence, 3),
            combined_confidence=combined_confidence,
        )

        return OracleResult(
            is_correct=is_correct,
            confidence=combined_confidence,
            detail=detail,
        )

    def _single_pass(
        self,
        test_code: str,
        endpoint_slice: dict,
        pass_num: int,
    ) -> dict[str, Any]:
        """
        Run one LLM evaluation pass.

        Returns a dict with keys: verdict, confidence, reason.
        On any error, returns a neutral/incorrect default so the vote is not
        artificially inflated by failures.
        """
        path = endpoint_slice.get("path", "?")
        method = endpoint_slice.get("method", "?").upper()
        operation = endpoint_slice.get("operation", {})
        expected_codes = list(operation.get("responses", {}).keys())

        user_prompt = (
            f"ENDPOINT: {method} {path}\n"
            f"EXPECTED STATUS CODES: {expected_codes}\n"
            f"OPERATION SUMMARY: {operation.get('summary', 'N/A')}\n\n"
            f"GENERATED TEST:\n```typescript\n{test_code[:3000]}\n```\n\n"
            "Do the assertions in this test correctly and meaningfully verify "
            "the endpoint behavior documented above? "
            "Respond with JSON only — no prose, no fences."
        )

        try:
            from cherenkov.ai import get_client
            from cherenkov.core.settings import get_settings

            client = get_client()
            # Slightly increasing temperature per pass to obtain independent samples
            temperature = round(0.05 + pass_num * 0.05, 2)
            response = client.complete_json(
                system_prompt=_EVAL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=get_settings().GEN_MODEL,
                temperature=temperature,
                run_id=None,
            )
            if isinstance(response, dict):
                verdict = response.get("verdict", "incorrect")
                confidence = min(1.0, max(0.0, float(response.get("confidence", 0.5))))
                reason = str(response.get("reason", ""))
                return {"verdict": verdict, "confidence": confidence, "reason": reason}
        except Exception as exc:
            self.log.warning(
                "consensus pass failed",
                pass_num=pass_num,
                error=str(exc),
            )

        # Neutral fallback: doesn't bias the vote toward correct
        return {
            "verdict": "incorrect",
            "confidence": 0.3,
            "reason": f"pass {pass_num} evaluation failed",
        }
