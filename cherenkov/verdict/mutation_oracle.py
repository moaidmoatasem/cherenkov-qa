"""
cherenkov/verdict/mutation_oracle.py — Mutation Oracle.

Inspired by Mutahunter (LLM-based mutation testing) and Diffblue Cover
(deterministic regression proofs).

Injects known-wrong mutations into the divergence proof and measures how
many the detection engine correctly catches.  A high mutation_score (≥0.80)
means the detector has real teeth — it can't be fooled by trivial output.

Three mutation classes are tested:
  STATUS_FLIP   — expect a different status code than the one the server returns
  FIELD_DROP    — omit a required field from an expected response shape
  ENUM_BYPASS   — send a value outside the spec's enum and expect a 4xx

The oracle runs offline (no LLM needed) by using pre-baked mutations that
correspond to the proof run probes.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    Severity,
)
from cherenkov.divergence.witness import WitnessAgent


@dataclass
class Mutation:
    """One injected mutation to test the detection engine against."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mutation_class: str = "STATUS_FLIP"  # STATUS_FLIP | FIELD_DROP | ENUM_BYPASS
    description: str = ""
    hypothesis: DivergenceHypothesis | None = None
    expected_to_detect: bool = True  # the oracle knows if this should be caught


@dataclass
class MutationResult:
    mutation_id: str
    mutation_class: str
    detected: bool             # did the engine flag it as a divergence?
    expected_to_detect: bool
    correct: bool = False      # detected == expected_to_detect
    detail: str = ""


@dataclass
class MutationOracleReport:
    mutations_run: int
    detected: int
    missed: int
    score: float               # detected / mutations_run  (1.0 = perfect)
    results: list[MutationResult] = field(default_factory=list)
    duration_ms: int = 0


class MutationOracle:
    """
    Runs a suite of known mutations against the WitnessAgent and
    scores how many the engine correctly identifies.

    Usage::

        oracle = MutationOracle(base_url="https://petstore3.swagger.io/api/v3")
        report = oracle.run()
        print(f"Mutation score: {report.score:.0%}")
    """

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.witness = WitnessAgent(base_url=base_url, timeout=timeout)

    def run(self) -> MutationOracleReport:
        mutations = self._build_mutations()
        t0 = time.time()
        results: list[MutationResult] = []

        for mutation in mutations:
            result = self._evaluate(mutation)
            results.append(result)

        duration_ms = int((time.time() - t0) * 1000)
        detected = sum(1 for r in results if r.correct)
        return MutationOracleReport(
            mutations_run=len(results),
            detected=detected,
            missed=len(results) - detected,
            score=detected / len(results) if results else 1.0,
            results=results,
            duration_ms=duration_ms,
        )

    # ── private ───────────────────────────────────────────────────────────

    def _evaluate(self, mutation: Mutation) -> MutationResult:
        if mutation.hypothesis is None:
            return MutationResult(
                mutation_id=mutation.id,
                mutation_class=mutation.mutation_class,
                detected=False,
                expected_to_detect=mutation.expected_to_detect,
                correct=not mutation.expected_to_detect,
                detail="No hypothesis provided",
            )
        try:
            repro = self.witness.reproduce(mutation.hypothesis)
            detected = repro.reproduced
        except Exception as exc:
            detected = False
            detail = f"Witness error: {exc}"
        else:
            detail = repro.rejection_reason or ""
            if repro.evidence:
                detail = repro.evidence.diff[:120]

        correct = detected == mutation.expected_to_detect
        return MutationResult(
            mutation_id=mutation.id,
            mutation_class=mutation.mutation_class,
            detected=detected,
            expected_to_detect=mutation.expected_to_detect,
            correct=correct,
            detail=detail,
        )

    def _build_mutations(self) -> list[Mutation]:
        """
        Build a fixed suite of mutations against the Petstore proof run probes.
        These are known divergences — the oracle expects the engine to catch them.
        """
        mutations: list[Mutation] = []

        # ── STATUS_FLIP mutations ─────────────────────────────────────────
        # Send a request that should return 400 per spec; engine must detect
        # when server returns 200 instead.
        mutations.append(
            Mutation(
                mutation_class="STATUS_FLIP",
                description="Enum bypass on /pet/findByStatus — expect 400, server returns 200",
                hypothesis=DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D1_SPEC_CODE,
                    claim_a="spec: invalid status enum value → 400",
                    claim_b="implementation returns 200 for invalid enum value",
                    predicted_evidence="GET /pet/findByStatus?status=MUTATION_INJECTED returns 200",
                    severity=Severity.HIGH,
                    endpoint="GET /pet/findByStatus",
                    repro_steps=[
                        "Send GET /pet/findByStatus?status=MUTATION_INJECTED_VALUE",
                        "Expect 400 response per spec enum constraint",
                    ],
                ),
                expected_to_detect=True,
            )
        )

        # ── FIELD_DROP mutations ──────────────────────────────────────────
        # POST a Pet without the required photoUrls field; spec says 4xx.
        mutations.append(
            Mutation(
                mutation_class="FIELD_DROP",
                description="Required field 'photoUrls' omitted — expect 4xx, server accepts",
                hypothesis=DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D1_SPEC_CODE,
                    claim_a="spec: Pet.photoUrls is required; omitting it → 4xx",
                    claim_b="implementation accepts Pet without photoUrls and returns 200",
                    predicted_evidence='POST /pet with {"name":"mutation-test"} (no photoUrls) returns 200',
                    severity=Severity.HIGH,
                    endpoint="POST /pet",
                    repro_steps=[
                        'Send POST /pet with body {"name": "mutation-test-dog", "status": "available"}',
                        "Expect 400 or 422 because photoUrls is required per schema",
                    ],
                ),
                expected_to_detect=True,
            )
        )

        # ── ENUM_BYPASS mutation ──────────────────────────────────────────
        # Missing response headers that the spec documents.
        mutations.append(
            Mutation(
                mutation_class="ENUM_BYPASS",
                description="Missing X-Rate-Limit header on /user/login — spec requires it",
                hypothesis=DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D5_SPEC_PROD,
                    claim_a="spec: login response MUST include X-Rate-Limit header",
                    claim_b="production omits X-Rate-Limit header",
                    predicted_evidence="GET /user/login returns 200 without X-Rate-Limit header",
                    severity=Severity.MEDIUM,
                    endpoint="GET /user/login",
                    repro_steps=[
                        "Send GET /user/login?username=test&password=abc123",
                        "Expect X-Rate-Limit header in response per spec",
                    ],
                ),
                expected_to_detect=True,
            )
        )

        # ── NEGATIVE mutation — should NOT be detected as a divergence ────
        # A well-formed request that the server handles correctly.
        # The engine should NOT flag this — the spec and server agree.
        mutations.append(
            Mutation(
                mutation_class="STATUS_FLIP",
                description="Valid inventory request — engine should NOT falsely flag",
                hypothesis=DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D2_CODE_PROD,
                    claim_a="spec: GET /store/inventory returns 200 with JSON object",
                    claim_b="production returns a completely different format",
                    predicted_evidence="GET /store/inventory returns 500 or XML",
                    severity=Severity.LOW,
                    endpoint="GET /store/inventory",
                    repro_steps=[
                        "Send GET /store/inventory",
                        "Expect 500 status code",  # deliberately wrong expectation
                    ],
                ),
                expected_to_detect=False,  # we expect the engine to NOT detect this
            )
        )

        return mutations
