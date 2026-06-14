"""
Workflow strategy — the variation matrix (ADR-007, vision 19 §3).

Pure rule table: QAContext (+ artifact executability) → WorkflowVariant.
Deterministic and fully unit-tested; the LLM reasons *within* activities,
never about *which* activities run.
"""

from __future__ import annotations

from cherenkov.reasoning.domain.models import (
    Activity,
    Artifact,
    Depth,
    ExecutionMode,
    Maturity,
    QAContext,
    TestingStage,
    WorkflowVariant,
)

_A = Activity


def select_variant(context: QAContext, artifact: Artifact) -> WorkflowVariant:
    """Map the three variation axes to a concrete workflow."""
    stage, maturity = context.stage, context.maturity

    # Stage picks the activity skeleton.
    if stage == TestingStage.STATIC_REVIEW:
        activities = [_A.ANALYZE, _A.REVIEW, _A.REPORT]
    elif stage == TestingStage.EXPLORATORY:
        activities = [_A.ANALYZE, _A.RISK_ASSESS, _A.PLAN, _A.EXECUTE, _A.REPORT]
    elif stage == TestingStage.REGRESSION:
        activities = [_A.RISK_ASSESS, _A.PLAN, _A.DESIGN_CASES, _A.EXECUTE, _A.REPORT]
    else:  # FUNCTIONAL and RELEASE_GATE share the full chain
        activities = [
            _A.ANALYZE,
            _A.REVIEW,
            _A.RISK_ASSESS,
            _A.PLAN,
            _A.DESIGN_CASES,
            _A.EXECUTE,
            _A.REPORT,
        ]

    # Maturity gates execution: concept artifacts have nothing to run,
    # in-development surfaces only execute against mocks.
    execution_mode = ExecutionMode.LIVE
    if maturity == Maturity.CONCEPT or stage == TestingStage.STATIC_REVIEW:
        execution_mode = ExecutionMode.NONE
    elif maturity == Maturity.IN_DEVELOPMENT:
        execution_mode = ExecutionMode.MOCK

    # Artifact kind gates execution: a PRD or Figma file with no paired
    # runnable target can never execute.
    if not artifact.is_executable:
        execution_mode = ExecutionMode.NONE

    if execution_mode == ExecutionMode.NONE:
        activities = [a for a in activities if a != _A.EXECUTE]

    depth = _select_depth(maturity, stage)
    name = f"{context.artifact_kind.value}:{maturity.value}:{stage.value}"
    return WorkflowVariant(
        name=name, activities=activities, depth=depth, execution_mode=execution_mode
    )


def _select_depth(maturity: Maturity, stage: TestingStage) -> Depth:
    if stage == TestingStage.RELEASE_GATE:
        return Depth.EXHAUSTIVE
    if maturity == Maturity.CONCEPT:
        return Depth.DEEP  # deep critique of the artifact itself
    if maturity == Maturity.IN_DEVELOPMENT:
        return Depth.SHALLOW  # the surface is still moving
    return Depth.MEDIUM
