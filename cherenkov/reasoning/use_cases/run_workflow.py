"""
QA workflow orchestration (ADR-007 §2, §4).

classify → select variant → run the selected activities through a
ReasoningBackend → QAPlan. For openapi_spec artifacts the plan bridges
into Track A via `to_scenarios()`; execution itself stays with the
existing pipeline (D7: this module never edits or runs test code).
"""

from __future__ import annotations

from cherenkov.core.contracts import Scenario
from cherenkov.reasoning.adapters.heuristic import HeuristicReasoner
from cherenkov.reasoning.domain.classifier import classify_kind, infer_maturity
from cherenkov.reasoning.domain.models import (
    Activity,
    AnalysisResult,
    Artifact,
    ArtifactKind,
    Maturity,
    QAContext,
    QAPlan,
    TestCharter,
    TestingStage,
)
from cherenkov.reasoning.domain.strategy import select_variant
from cherenkov.reasoning.ports.reasoner import ReasoningBackend


class QAWorkflow:
    """Runs the artifact-adaptive QA workflow and produces a QAPlan."""

    def __init__(self, reasoner: ReasoningBackend | None = None):
        self.reasoner: ReasoningBackend = reasoner or HeuristicReasoner()

    def run(
        self,
        artifact: Artifact,
        stage: TestingStage | None = None,
        maturity: Maturity | None = None,
    ) -> QAPlan:
        context = QAContext(
            artifact_kind=artifact.kind,
            maturity=maturity or infer_maturity(artifact),
            stage=stage or TestingStage.FUNCTIONAL,
        )
        variant = select_variant(context, artifact)
        plan = QAPlan(context=context, variant=variant, artifact_name=artifact.name)

        analysis = AnalysisResult()
        for activity in variant.activities:
            if activity == Activity.ANALYZE:
                analysis = self.reasoner.analyze(artifact, variant.depth)
                plan = plan.model_copy(update={"analysis": analysis})
            elif activity == Activity.REVIEW:
                plan = plan.model_copy(
                    update={
                        "findings": self.reasoner.review(
                            artifact, analysis, variant.depth
                        )
                    }
                )
            elif activity == Activity.RISK_ASSESS:
                if not analysis.requirements:
                    analysis = self.reasoner.analyze(artifact, variant.depth)
                    plan = plan.model_copy(update={"analysis": analysis})
                plan = plan.model_copy(
                    update={
                        "risks": self.reasoner.assess_risks(
                            artifact, analysis, variant.depth
                        )
                    }
                )
            elif (
                activity == Activity.PLAN and context.stage == TestingStage.EXPLORATORY
            ):
                plan = plan.model_copy(update={"charters": _charters_from_risks(plan)})
            elif activity == Activity.DESIGN_CASES:
                cases = self.reasoner.design_cases(
                    artifact, analysis, plan.risks, variant.depth
                )
                plan = QAPlan(
                    **{**plan.model_dump(), "cases": [c.model_dump() for c in cases]}
                )
            # EXECUTE and REPORT are carried out by downstream consumers
            # (Track A pipeline / explorer / report emitters) — see ADR-007 §4.
        return plan


def _charters_from_risks(plan: QAPlan) -> list[TestCharter]:
    charters: list[TestCharter] = []
    for risk in plan.risks[:5]:
        charters.append(
            TestCharter(
                id=f"CH-{len(charters) + 1:02d}",
                mission=f"Explore for: {risk.description[:90]}",
                areas=risk.requirement_refs,
                risk_refs=[risk.id],
            )
        )
    return charters


def build_artifact(
    name: str,
    uri: str = "",
    content: str = "",
    parsed: dict | None = None,
    kind: ArtifactKind | None = None,
    target_url: str = "",
) -> Artifact:
    """Construct an Artifact, classifying its kind when not stated."""
    parsed = parsed or {}
    return Artifact(
        kind=kind or classify_kind(uri=uri, content=content, parsed=parsed),
        name=name,
        uri=uri,
        content=content,
        parsed=parsed,
        target_url=target_url,
    )


def to_scenarios(plan: QAPlan) -> list[Scenario]:
    """Bridge designed cases into Track A scenarios (openapi_spec only).

    Only cases whose endpoint/method/status were bound from the spec are
    converted — the reasoner prioritizes and drops, it never invents an
    expected status (spec-derived invariant).
    """
    scenarios: list[Scenario] = []
    for case in plan.cases:
        if not case.endpoint or case.expected_status is None:
            continue
        scenarios.append(
            Scenario(
                endpoint=case.endpoint,
                method=case.method,
                case_type=case.case_type or "happy_path",
                priority=case.priority,
                mutation_id=case.mutation_id,
                expected_status=case.expected_status,
            )
        )
    return scenarios
