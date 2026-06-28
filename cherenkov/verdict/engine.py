"""
cherenkov/verdict/engine.py — Parallel multi-agent verdict engine.

Inspired by TestSprite's fleet-of-parallel-agents model and Qodo's
multi-agent PR review (bug agent + quality agent + security agent + coverage agent).

Runs 4 specialised agents concurrently via ThreadPoolExecutor:
  1. DivergenceProbe   — existing proof_run (Skeptic → Witness loop)
  2. MutationOracle    — measures detection engine's mutation kill rate
  3. SemanticJudge     — LLM-as-judge for evidence quality
  4. CoverageAnalyzer  — spec endpoint coverage gap report

Each agent returns a VerdictDimension.  The engine assembles a RichVerdict
from all dimension results plus aggregate metrics.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import DivergenceReport
from cherenkov.verdict.models import (
    OverallVerdict,
    RichVerdict,
    VerdictDimension,
    VerdictGrade,
    assemble_verdict,
    score_to_grade,
)


class VerdictEngine:
    """
    Orchestrates the parallel multi-agent verdict pipeline.

    Usage::

        engine = VerdictEngine(
            base_url="https://petstore3.swagger.io/api/v3",
            spec=None,           # use built-in Petstore demo spec
            use_llm=False,       # offline mode
        )
        rich = engine.run()
        print(rich.render())
    """

    def __init__(
        self,
        base_url: str,
        spec: dict | None = None,
        spec_source: str = "built-in",
        use_llm: bool = False,
        run_mutation_oracle: bool = True,
        run_semantic_judge: bool = True,
        run_traffic_capture: bool = True,
        fixture_dir: str | Path = ".cherenkov/fixtures",
        max_workers: int = 4,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url
        self.spec = spec
        self.spec_source = spec_source
        self.use_llm = use_llm
        self.run_mutation_oracle = run_mutation_oracle
        self.run_semantic_judge = run_semantic_judge
        self.run_traffic_capture = run_traffic_capture
        self.fixture_dir = Path(fixture_dir)
        self.max_workers = max_workers
        self.timeout = timeout

    def run(self) -> RichVerdict:
        """Execute all agents in parallel and assemble the RichVerdict."""
        t0 = time.time()
        run_id = str(uuid.uuid4())[:8]

        # ── Stage 1: Divergence Probe (always runs first — others depend on it) ─
        divergence_dim, divergence_reports = self._run_divergence_probe()

        # ── Stage 2: parallel agents ──────────────────────────────────────
        futures: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures["coverage"] = pool.submit(self._run_coverage_analyzer, divergence_reports)

            if self.run_mutation_oracle:
                futures["mutation"] = pool.submit(self._run_mutation_oracle)

            if self.run_semantic_judge:
                futures["semantic"] = pool.submit(self._run_semantic_judge, divergence_reports)

            if self.run_traffic_capture:
                futures["traffic"] = pool.submit(
                    self._run_traffic_capture, divergence_reports
                )

        # ── Stage 3: collect results ──────────────────────────────────────
        dimensions: list[VerdictDimension] = [divergence_dim]

        coverage_pct = 0.0
        mutation_score: float | None = None
        semantic_score: float | None = None
        captured_fixtures = 0

        for key, future in futures.items():
            try:
                result = future.result(timeout=60)
            except Exception as exc:
                dimensions.append(
                    VerdictDimension(
                        name=_dim_name(key),
                        score=0.5,
                        grade=VerdictGrade.C,
                        passed=False,
                        findings=[f"Agent error: {exc}"],
                        detail=str(exc),
                    )
                )
                continue

            if key == "coverage":
                dim, pct = result
                dimensions.append(dim)
                coverage_pct = pct

            elif key == "mutation":
                dim, score = result
                dimensions.append(dim)
                mutation_score = score

            elif key == "semantic":
                dim, score = result
                dimensions.append(dim)
                semantic_score = score

            elif key == "traffic":
                dim, count = result
                dimensions.append(dim)
                captured_fixtures = count

        duration_ms = int((time.time() - t0) * 1000)

        return assemble_verdict(
            target_url=self.base_url,
            spec_source=self.spec_source,
            dimensions=dimensions,
            divergence_reports=divergence_reports,
            coverage_pct=coverage_pct,
            mutation_score=mutation_score,
            semantic_score=semantic_score,
            captured_fixtures=captured_fixtures,
            duration_ms=duration_ms,
        )

    # ── individual agent runners ──────────────────────────────────────────

    def _run_divergence_probe(
        self,
    ) -> tuple[VerdictDimension, list[DivergenceReport]]:
        from cherenkov.divergence.proof_run import run_proof

        t0 = time.time()
        try:
            reports = run_proof(
                base_url=self.base_url,
                spec=self.spec,
                use_llm=self.use_llm,
            )
        except Exception as exc:
            return (
                VerdictDimension(
                    name="divergence_probe",
                    score=0.0,
                    grade=VerdictGrade.F,
                    passed=False,
                    findings=[f"Probe failed: {exc}"],
                    detail=str(exc),
                    duration_ms=int((time.time() - t0) * 1000),
                ),
                [],
            )

        duration_ms = int((time.time() - t0) * 1000)
        n = len(reports)
        # Score: 1.0 if no divergences, degrades by severity
        from cherenkov.core.contracts import Severity

        penalty = sum(
            0.3 if getattr(r, "severity", None) in (Severity.CRITICAL, "critical")
            else 0.2 if getattr(r, "severity", None) in (Severity.HIGH, "high")
            else 0.1 if getattr(r, "severity", None) in (Severity.MEDIUM, "medium")
            else 0.05
            for r in reports
        )
        score = max(0.0, 1.0 - penalty)
        passed = score >= 0.6

        findings = [
            f"[{str(getattr(r, 'severity', '')).split('.')[-1].upper()}] "
            f"{getattr(r, 'endpoint', '')} — {str(getattr(r, 'claim_a', ''))[:60]}"
            for r in reports
        ]
        return (
            VerdictDimension(
                name="divergence_probe",
                score=score,
                grade=score_to_grade(score),
                passed=passed,
                findings=findings,
                detail=f"{n} divergence(s) confirmed",
                duration_ms=duration_ms,
            ),
            reports,
        )

    def _run_coverage_analyzer(
        self, reports: list[DivergenceReport]
    ) -> tuple[VerdictDimension, float]:
        from cherenkov.divergence.coverage import compute_coverage

        t0 = time.time()
        spec = self.spec
        if spec is None:
            from cherenkov.divergence.proof_run import PETSTORE_SPEC_SUBSET
            spec = PETSTORE_SPEC_SUBSET

        try:
            cov = compute_coverage(spec, reports)
            pct = cov.coverage_pct
        except Exception:
            pct = 0.0

        duration_ms = int((time.time() - t0) * 1000)
        score = pct / 100.0
        passed = pct >= 60.0
        findings = []
        if pct < 60.0:
            findings.append(f"Only {pct:.0f}% of spec endpoints probed")

        return (
            VerdictDimension(
                name="spec_coverage",
                score=score,
                grade=score_to_grade(score),
                passed=passed,
                findings=findings,
                detail=f"{pct:.1f}% coverage",
                duration_ms=duration_ms,
            ),
            pct,
        )

    def _run_mutation_oracle(self) -> tuple[VerdictDimension, float]:
        from cherenkov.verdict.mutation_oracle import MutationOracle

        t0 = time.time()
        try:
            oracle = MutationOracle(base_url=self.base_url, timeout=self.timeout)
            report = oracle.run()
            score = report.score
        except Exception as exc:
            return (
                VerdictDimension(
                    name="mutation_oracle",
                    score=0.5,
                    grade=VerdictGrade.C,
                    passed=False,
                    findings=[f"Oracle error: {exc}"],
                    detail=str(exc),
                    duration_ms=int((time.time() - t0) * 1000),
                ),
                0.5,
            )

        duration_ms = int((time.time() - t0) * 1000)
        passed = score >= 0.75
        missed = [r for r in report.results if not r.correct]
        findings = [
            f"Mutation not caught: {r.mutation_class} — {r.detail[:60]}"
            for r in missed[:3]
        ]
        return (
            VerdictDimension(
                name="mutation_oracle",
                score=score,
                grade=score_to_grade(score),
                passed=passed,
                findings=findings,
                detail=f"{report.detected}/{report.mutations_run} mutations correctly handled",
                duration_ms=duration_ms,
            ),
            score,
        )

    def _run_semantic_judge(
        self, reports: list[DivergenceReport]
    ) -> tuple[VerdictDimension, float]:
        from cherenkov.verdict.semantic_judge import SemanticJudge

        t0 = time.time()
        try:
            judge = SemanticJudge(run_id=None)
            report = judge.evaluate(reports, use_llm=self.use_llm)
            score = report.aggregate_score
        except Exception as exc:
            return (
                VerdictDimension(
                    name="semantic_judge",
                    score=0.5,
                    grade=VerdictGrade.C,
                    passed=False,
                    findings=[f"Judge error: {exc}"],
                    detail=str(exc),
                    duration_ms=int((time.time() - t0) * 1000),
                ),
                0.5,
            )

        duration_ms = int((time.time() - t0) * 1000)
        passed = score >= 0.65
        weak = [e for e in report.evaluations if e.label in ("weak", "false_positive")]
        findings = [
            f"Low-quality evidence [{e.label}]: {e.rationale[:60]}"
            for e in weak[:3]
        ]
        return (
            VerdictDimension(
                name="semantic_judge",
                score=score,
                grade=score_to_grade(score),
                passed=passed,
                findings=findings,
                detail=f"avg quality {score:.0%} ({report.provider})",
                duration_ms=duration_ms,
            ),
            score,
        )

    def _run_traffic_capture(
        self, reports: list[DivergenceReport]
    ) -> tuple[VerdictDimension, int]:
        from cherenkov.verdict.traffic_capture import TrafficCapture
        from cherenkov.divergence.proof_run import PROOF_RUN_PROBES, PETSTORE_SPEC_SUBSET
        from cherenkov.divergence.proof_run import _offline_hypotheses

        t0 = time.time()
        try:
            capture = TrafficCapture(base_url=self.base_url, timeout=self.timeout)
            hypotheses = []
            for endpoint, method, _, _ in PROOF_RUN_PROBES:
                hypotheses.extend(_offline_hypotheses(endpoint, method))

            cap_report = capture.run(hypotheses, fixture_dir=self.fixture_dir)
            golden = cap_report.golden_count
        except Exception as exc:
            return (
                VerdictDimension(
                    name="traffic_capture",
                    score=0.5,
                    grade=VerdictGrade.C,
                    passed=True,
                    findings=[f"Capture error (non-fatal): {exc}"],
                    detail=str(exc),
                    duration_ms=int((time.time() - t0) * 1000),
                ),
                0,
            )

        duration_ms = int((time.time() - t0) * 1000)
        score = min(1.0, golden / max(1, len(hypotheses)))
        return (
            VerdictDimension(
                name="traffic_capture",
                score=score,
                grade=score_to_grade(score),
                passed=True,
                findings=[],
                detail=f"{golden} golden fixture(s) captured",
                duration_ms=duration_ms,
            ),
            golden,
        )


def _dim_name(key: str) -> str:
    return {
        "coverage": "spec_coverage",
        "mutation": "mutation_oracle",
        "semantic": "semantic_judge",
        "traffic": "traffic_capture",
    }.get(key, key)
