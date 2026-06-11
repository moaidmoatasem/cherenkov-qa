"""Unit tests for the QA Reasoning Engine (ADR-007) — pure domain, no I/O."""
from __future__ import annotations

import pytest

from cherenkov.reasoning.adapters.heuristic import HeuristicReasoner
from cherenkov.reasoning.domain.classifier import classify_kind, infer_maturity
from cherenkov.reasoning.domain.models import (
    Activity,
    AnalysisResult,
    Artifact,
    ArtifactKind,
    Depth,
    ExecutionMode,
    FindingCategory,
    Maturity,
    QAContext,
    QAPlan,
    Requirement,
    TestCaseDesign,
    TestingStage,
    WorkflowVariant,
    priority_from_score,
)
from cherenkov.reasoning.domain.strategy import select_variant
from cherenkov.reasoning.use_cases.run_workflow import (
    QAWorkflow,
    build_artifact,
    to_scenarios,
)

PETSTORE = {
    "openapi": "3.0.0",
    "info": {"title": "Petstore", "version": "1.2.0"},
    "paths": {
        "/pets": {
            "get": {
                "summary": "List pets",
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "summary": "Create pet",
                "responses": {
                    "201": {"description": "created"},
                    "422": {"description": "validation error"},
                },
            },
        },
        "/users": {
            "post": {
                "responses": {"201": {"description": "created"}},
            },
        },
    },
}

PRD = """\
# Checkout PRD

The system shall process payment within the session.
Users must be able to reset their password via email.
The UI should be fast and user-friendly.
"""


# ── classifier ────────────────────────────────────────────────────────────

class TestClassifier:
    def test_openapi_from_parsed(self):
        assert classify_kind(parsed=PETSTORE) == ArtifactKind.OPENAPI_SPEC

    def test_figma_url(self):
        assert classify_kind(uri="https://figma.com/design/abc/My-App") == ArtifactKind.FIGMA_DESIGN

    def test_live_app_url(self):
        assert classify_kind(uri="http://localhost:8000") == ArtifactKind.LIVE_APP

    def test_source_file_is_codebase(self):
        assert classify_kind(uri="app/src/main.py") == ArtifactKind.CODEBASE

    def test_default_is_requirements_doc(self):
        assert classify_kind(content=PRD) == ArtifactKind.REQUIREMENTS_DOC

    def test_openapi_yaml_by_content(self):
        assert classify_kind(uri="spec.yaml", content='openapi: "3.0.0"') == ArtifactKind.OPENAPI_SPEC

    def test_maturity_zero_version_is_in_development(self):
        spec = {**PETSTORE, "info": {"title": "x", "version": "0.3.0"}}
        artifact = Artifact(kind=ArtifactKind.OPENAPI_SPEC, name="s", parsed=spec)
        assert infer_maturity(artifact) == Maturity.IN_DEVELOPMENT

    def test_maturity_draft_marker_is_concept(self):
        artifact = Artifact(
            kind=ArtifactKind.REQUIREMENTS_DOC, name="prd", content="DRAFT: " + PRD
        )
        assert infer_maturity(artifact) == Maturity.CONCEPT

    def test_maturity_live_app_is_production(self):
        artifact = Artifact(kind=ArtifactKind.LIVE_APP, name="app", uri="https://x.io")
        assert infer_maturity(artifact) == Maturity.PRODUCTION


# ── strategy: the variation matrix ────────────────────────────────────────

class TestStrategy:
    def _ctx(self, kind, maturity, stage):
        return QAContext(artifact_kind=kind, maturity=maturity, stage=stage)

    def _spec_artifact(self):
        return Artifact(
            kind=ArtifactKind.OPENAPI_SPEC, name="s", parsed=PETSTORE,
            target_url="http://localhost:8000",
        )

    def test_concept_never_executes(self):
        variant = select_variant(
            self._ctx(ArtifactKind.OPENAPI_SPEC, Maturity.CONCEPT, TestingStage.FUNCTIONAL),
            self._spec_artifact(),
        )
        assert Activity.EXECUTE not in variant.activities
        assert variant.execution_mode == ExecutionMode.NONE
        assert variant.depth == Depth.DEEP

    def test_static_review_is_critique_only(self):
        variant = select_variant(
            self._ctx(ArtifactKind.REQUIREMENTS_DOC, Maturity.PRODUCTION, TestingStage.STATIC_REVIEW),
            Artifact(kind=ArtifactKind.REQUIREMENTS_DOC, name="prd", content=PRD),
        )
        assert variant.activities == [Activity.ANALYZE, Activity.REVIEW, Activity.REPORT]

    def test_in_development_executes_against_mock_only(self):
        variant = select_variant(
            self._ctx(ArtifactKind.OPENAPI_SPEC, Maturity.IN_DEVELOPMENT, TestingStage.FUNCTIONAL),
            self._spec_artifact(),
        )
        assert variant.execution_mode == ExecutionMode.MOCK

    def test_release_gate_is_exhaustive_and_live(self):
        variant = select_variant(
            self._ctx(ArtifactKind.OPENAPI_SPEC, Maturity.PRODUCTION, TestingStage.RELEASE_GATE),
            self._spec_artifact(),
        )
        assert variant.depth == Depth.EXHAUSTIVE
        assert variant.execution_mode == ExecutionMode.LIVE
        assert Activity.EXECUTE in variant.activities

    def test_prd_without_target_never_executes(self):
        variant = select_variant(
            self._ctx(ArtifactKind.REQUIREMENTS_DOC, Maturity.PRODUCTION, TestingStage.REGRESSION),
            Artifact(kind=ArtifactKind.REQUIREMENTS_DOC, name="prd", content=PRD),
        )
        assert variant.execution_mode == ExecutionMode.NONE
        assert Activity.EXECUTE not in variant.activities

    def test_prd_with_target_may_execute(self):
        variant = select_variant(
            self._ctx(ArtifactKind.REQUIREMENTS_DOC, Maturity.PRODUCTION, TestingStage.REGRESSION),
            Artifact(
                kind=ArtifactKind.REQUIREMENTS_DOC, name="prd", content=PRD,
                target_url="http://localhost:8000",
            ),
        )
        assert Activity.EXECUTE in variant.activities

    def test_variant_contract_rejects_execute_without_mode(self):
        with pytest.raises(ValueError):
            WorkflowVariant(
                name="bad",
                activities=[Activity.EXECUTE],
                depth=Depth.SHALLOW,
                execution_mode=ExecutionMode.NONE,
            )


# ── heuristic reasoner ────────────────────────────────────────────────────

class TestHeuristicReasoner:
    def test_spec_analysis_extracts_response_requirements(self):
        artifact = Artifact(kind=ArtifactKind.OPENAPI_SPEC, name="s", parsed=PETSTORE)
        analysis = HeuristicReasoner().analyze(artifact, Depth.MEDIUM)
        assert analysis.surface_size == 3
        texts = [r.text for r in analysis.requirements]
        assert "POST /pets responds 422 per spec" in texts
        assert any("no description" in a for a in analysis.ambiguities)

    def test_prd_analysis_flags_vague_requirements(self):
        artifact = Artifact(kind=ArtifactKind.REQUIREMENTS_DOC, name="prd", content=PRD)
        analysis = HeuristicReasoner().analyze(artifact, Depth.MEDIUM)
        assert len(analysis.requirements) == 3
        vague = [r for r in analysis.requirements if not r.testable]
        assert len(vague) == 1
        assert "user-friendly" in vague[0].text

    def test_spec_review_finds_missing_4xx_and_open_mutation(self):
        artifact = Artifact(kind=ArtifactKind.OPENAPI_SPEC, name="s", parsed=PETSTORE)
        reasoner = HeuristicReasoner()
        analysis = reasoner.analyze(artifact, Depth.MEDIUM)
        findings = reasoner.review(artifact, analysis, Depth.MEDIUM)
        gaps = [f for f in findings if f.category == FindingCategory.GAP]
        assert any("POST /users" in f.description for f in gaps)
        risks = [f for f in findings if f.category == FindingCategory.RISK]
        assert any("no security requirement" in f.description for f in risks)

    def test_risks_are_traced_and_sorted(self):
        artifact = Artifact(kind=ArtifactKind.REQUIREMENTS_DOC, name="prd", content=PRD)
        reasoner = HeuristicReasoner()
        analysis = reasoner.analyze(artifact, Depth.MEDIUM)
        risks = reasoner.assess_risks(artifact, analysis, Depth.MEDIUM)
        assert all(r.requirement_refs for r in risks)
        scores = [r.score for r in risks]
        assert scores == sorted(scores, reverse=True)
        # payment + password requirements carry higher impact than UI fluff
        assert "payment" in risks[0].description.lower() or "password" in risks[0].description.lower()

    def test_designed_cases_trace_to_requirements_and_risks(self):
        artifact = Artifact(kind=ArtifactKind.OPENAPI_SPEC, name="s", parsed=PETSTORE)
        reasoner = HeuristicReasoner()
        analysis = reasoner.analyze(artifact, Depth.MEDIUM)
        risks = reasoner.assess_risks(artifact, analysis, Depth.MEDIUM)
        cases = reasoner.design_cases(artifact, analysis, risks, Depth.MEDIUM)
        assert cases
        for case in cases:
            assert case.requirement_ref
            assert case.rationale
        bound = [c for c in cases if c.expected_status is not None]
        assert {c.expected_status for c in bound} == {200, 201, 422}

    def test_shallow_depth_caps_output(self):
        big_spec = {
            "openapi": "3.0.0",
            "info": {"title": "big", "version": "1.0.0"},
            "paths": {
                f"/r{i}": {"get": {"responses": {"200": {"description": "ok"}}}}
                for i in range(50)
            },
        }
        artifact = Artifact(kind=ArtifactKind.OPENAPI_SPEC, name="big", parsed=big_spec)
        analysis = HeuristicReasoner().analyze(artifact, Depth.SHALLOW)
        assert len(analysis.requirements) == 10
        assert analysis.surface_size == 50


# ── plan contract ─────────────────────────────────────────────────────────

class TestQAPlanContract:
    def test_untraced_case_is_rejected(self):
        context = QAContext(artifact_kind=ArtifactKind.OPENAPI_SPEC)
        variant = WorkflowVariant(
            name="v", activities=[Activity.DESIGN_CASES],
            depth=Depth.SHALLOW, execution_mode=ExecutionMode.NONE,
        )
        with pytest.raises(ValueError, match="traces to no known requirement"):
            QAPlan(
                context=context,
                variant=variant,
                artifact_name="s",
                analysis=AnalysisResult(requirements=[Requirement(id="REQ-001", text="x")]),
                cases=[
                    TestCaseDesign(
                        id="TC-001", title="orphan", requirement_ref="REQ-999",
                        rationale="invented",
                    )
                ],
            )

    def test_priority_from_score_bands(self):
        assert priority_from_score(25) == "P1"
        assert priority_from_score(15) == "P1"
        assert priority_from_score(8) == "P2"
        assert priority_from_score(4) == "P3"


# ── end-to-end workflow + Track A bridge ──────────────────────────────────

class TestQAWorkflow:
    def test_functional_workflow_on_spec_produces_scenarios(self):
        artifact = build_artifact(
            name="petstore", parsed=PETSTORE, target_url="http://localhost:8000"
        )
        plan = QAWorkflow().run(
            artifact, stage=TestingStage.FUNCTIONAL, maturity=Maturity.STABILIZING
        )
        assert plan.variant.execution_mode == ExecutionMode.LIVE
        assert plan.findings and plan.risks and plan.cases
        scenarios = to_scenarios(plan)
        assert scenarios
        for s in scenarios:
            # spec-derived invariant: every expected status exists in the spec
            responses = PETSTORE["paths"][s.endpoint][s.method.lower()]["responses"]
            assert str(s.expected_status) in responses

    def test_static_review_on_concept_prd_produces_critique_only(self):
        artifact = build_artifact(name="checkout-prd", content="DRAFT\n" + PRD)
        plan = QAWorkflow().run(artifact, stage=TestingStage.STATIC_REVIEW)
        assert plan.context.maturity == Maturity.CONCEPT
        assert plan.findings
        assert not plan.cases
        assert plan.variant.execution_mode == ExecutionMode.NONE

    def test_exploratory_workflow_produces_charters(self):
        artifact = build_artifact(name="app", uri="http://localhost:3000", content=PRD)
        plan = QAWorkflow().run(artifact, stage=TestingStage.EXPLORATORY)
        assert artifact.kind == ArtifactKind.LIVE_APP
        assert plan.charters
        assert all(ch.risk_refs for ch in plan.charters)

    def test_regression_workflow_lazily_analyzes(self):
        artifact = build_artifact(
            name="petstore", parsed=PETSTORE, target_url="http://localhost:8000"
        )
        plan = QAWorkflow().run(
            artifact, stage=TestingStage.REGRESSION, maturity=Maturity.PRODUCTION
        )
        # regression skeleton has no ANALYZE activity, but risk assessment
        # needs requirements — the workflow back-fills the analysis
        assert plan.analysis.requirements
        assert plan.cases

    def test_prd_workflow_yields_plan_without_scenarios(self):
        artifact = build_artifact(name="prd", content=PRD)
        plan = QAWorkflow().run(artifact, stage=TestingStage.FUNCTIONAL)
        assert plan.cases
        assert to_scenarios(plan) == []
