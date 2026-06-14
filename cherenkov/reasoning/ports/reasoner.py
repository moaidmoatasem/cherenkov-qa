"""ReasoningBackend port — the 'how to think' boundary (ADR-007 §3)."""

from __future__ import annotations

from typing import Protocol

from cherenkov.reasoning.domain.models import (
    AnalysisResult,
    Artifact,
    Depth,
    ReviewFinding,
    RiskItem,
    TestCaseDesign,
)


class ReasoningBackend(Protocol):
    """Adapters: HeuristicReasoner (L0, deterministic), OllamaReasoner (follow-up)."""

    def analyze(self, artifact: Artifact, depth: Depth) -> AnalysisResult:
        """Extract intent, testable requirements, and ambiguities."""
        ...

    def review(
        self, artifact: Artifact, analysis: AnalysisResult, depth: Depth
    ) -> list[ReviewFinding]:
        """Critique the artifact itself: gaps, contradictions, untestable items."""
        ...

    def assess_risks(
        self, artifact: Artifact, analysis: AnalysisResult, depth: Depth
    ) -> list[RiskItem]:
        """Produce a risk register traced to requirements."""
        ...

    def design_cases(
        self,
        artifact: Artifact,
        analysis: AnalysisResult,
        risks: list[RiskItem],
        depth: Depth,
    ) -> list[TestCaseDesign]:
        """Design traceable test cases, prioritized by risk score."""
        ...
