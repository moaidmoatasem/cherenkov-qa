"""
Domain models for the QA Reasoning Engine (ADR-007).

Pure Python — no I/O, no LLM calls. These types are the contract between
the workflow strategy, the reasoning backends, and the Track A bridge.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, model_validator


class ArtifactKind(str, Enum):
    OPENAPI_SPEC = "openapi_spec"
    REQUIREMENTS_DOC = "requirements_doc"
    FIGMA_DESIGN = "figma_design"
    CODEBASE = "codebase"
    LIVE_APP = "live_app"


class Maturity(str, Enum):
    CONCEPT = "concept"               # idea/draft — nothing runnable
    IN_DEVELOPMENT = "in_development"  # being built — unstable surface
    STABILIZING = "stabilizing"        # feature-complete, hardening
    PRODUCTION = "production"          # shipped — regressions are expensive


class TestingStage(str, Enum):
    __test__ = False  # not a pytest class despite the Test prefix
    STATIC_REVIEW = "static_review"    # critique the artifact, run nothing
    EXPLORATORY = "exploratory"        # charter-based discovery
    FUNCTIONAL = "functional"          # scripted verification of behavior
    REGRESSION = "regression"          # breadth-first re-verification
    RELEASE_GATE = "release_gate"      # evidence-grade, exhaustive


class Activity(str, Enum):
    ANALYZE = "analyze"
    REVIEW = "review"
    RISK_ASSESS = "risk_assess"
    PLAN = "plan"
    DESIGN_CASES = "design_cases"
    EXECUTE = "execute"
    REPORT = "report"


class Depth(str, Enum):
    SHALLOW = "shallow"
    MEDIUM = "medium"
    DEEP = "deep"
    EXHAUSTIVE = "exhaustive"


class ExecutionMode(str, Enum):
    NONE = "none"      # nothing is run
    MOCK = "mock"      # Prism / stub targets only
    LIVE = "live"      # real target


class Artifact(BaseModel):
    """An input the engine reasons over. Content is raw text or a parsed dict."""
    kind: ArtifactKind
    name: str
    uri: str = ""                      # path, URL, or figma link
    content: str = ""                  # raw text (PRD, spec source, ...)
    parsed: dict = Field(default_factory=dict)  # e.g. parsed OpenAPI document
    target_url: str = ""               # runnable target paired with the artifact, if any

    @property
    def is_executable(self) -> bool:
        """An artifact is executable if it is itself runnable or paired with a target."""
        if self.kind in (ArtifactKind.LIVE_APP, ArtifactKind.CODEBASE):
            return True
        return bool(self.target_url)


class QAContext(BaseModel):
    """The three variation axes: what, how mature, and which stage of testing."""
    artifact_kind: ArtifactKind
    maturity: Maturity = Maturity.IN_DEVELOPMENT
    stage: TestingStage = TestingStage.FUNCTIONAL


class WorkflowVariant(BaseModel):
    """A selected QA workflow: which activities run, how deep, what executes."""
    name: str
    activities: list[Activity]
    depth: Depth
    execution_mode: ExecutionMode

    @model_validator(mode="after")
    def _execute_requires_mode(self) -> "WorkflowVariant":
        has_execute = Activity.EXECUTE in self.activities
        if has_execute and self.execution_mode == ExecutionMode.NONE:
            raise ValueError("variant includes EXECUTE but execution_mode is NONE")
        if not has_execute and self.execution_mode != ExecutionMode.NONE:
            raise ValueError("execution_mode set but EXECUTE not in activities")
        return self


# ── Reasoning outputs ─────────────────────────────────────────────────────

class Requirement(BaseModel):
    """A testable statement extracted from the artifact."""
    id: str
    text: str
    source_ref: str = ""               # endpoint, doc section, frame name, ...
    testable: bool = True


class AnalysisResult(BaseModel):
    intents: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    surface_size: int = 0              # endpoints / screens / flows discovered


class FindingCategory(str, Enum):
    GAP = "gap"
    CONTRADICTION = "contradiction"
    UNTESTABLE = "untestable"
    RISK = "risk"
    QUALITY = "quality"


class ReviewFinding(BaseModel):
    """A critique of the artifact itself — produced before any test exists."""
    category: FindingCategory
    severity: str = "medium"           # low | medium | high
    description: str
    recommendation: str = ""
    source_ref: str = ""


class RiskItem(BaseModel):
    id: str
    description: str
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    requirement_refs: list[str] = Field(default_factory=list)

    @property
    def score(self) -> int:
        return self.likelihood * self.impact


def priority_from_score(score: int) -> str:
    """Risk score (1-25) → P1/P2/P3. Replaces the hardcoded case-type rule."""
    if score >= 15:
        return "P1"
    if score >= 8:
        return "P2"
    return "P3"


class TestCaseDesign(BaseModel):
    """A designed test case — traceable to a requirement and the risks it mitigates."""
    __test__ = False  # not a pytest class despite the Test prefix
    id: str
    title: str
    requirement_ref: str
    risk_refs: list[str] = Field(default_factory=list)
    rationale: str
    steps: list[str] = Field(default_factory=list)
    expected: str = ""
    priority: str = "P2"
    # Bridge fields — populated only for openapi_spec artifacts, always
    # SELECTED from the spec-derived mutation menu, never invented.
    endpoint: str = ""
    method: str = ""
    case_type: str = ""
    mutation_id: str | None = None
    expected_status: int | None = None


class TestCharter(BaseModel):
    """An exploratory session charter (stage=exploratory)."""
    id: str
    mission: str
    areas: list[str] = Field(default_factory=list)
    risk_refs: list[str] = Field(default_factory=list)
    timebox_minutes: int = 30


class QAPlan(BaseModel):
    """The engine's product: everything needed to act, with full traceability."""
    context: QAContext
    variant: WorkflowVariant
    artifact_name: str
    analysis: AnalysisResult = Field(default_factory=AnalysisResult)
    findings: list[ReviewFinding] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    cases: list[TestCaseDesign] = Field(default_factory=list)
    charters: list[TestCharter] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cases_must_trace(self) -> "QAPlan":
        req_ids = {r.id for r in self.analysis.requirements}
        risk_ids = {r.id for r in self.risks}
        for case in self.cases:
            traced = case.requirement_ref in req_ids or any(
                ref in risk_ids for ref in case.risk_refs
            )
            if not traced:
                raise ValueError(
                    f"case {case.id!r} traces to no known requirement or risk "
                    f"(requirement_ref={case.requirement_ref!r}, risk_refs={case.risk_refs})"
                )
        return self
