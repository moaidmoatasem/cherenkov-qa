"""
CHERENKOV core/contracts.py — the typed boundaries between every pipeline stage.
Authority: v3.1 + delta. These are the Pydantic contracts the whole DAG enforces.

A stage that emits data failing its contract fails LOUDLY here, at the boundary,
instead of silently corrupting the next stage. Versioned so a model/prompt change
can't quietly break a downstream consumer.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class Status(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"   # produced output, but with caveats (e.g. thin spec)
    FAILED = "failed"


class StageMeta(BaseModel):
    stage: str
    model: str | None = None
    tokens: int = 0
    duration_ms: int = 0
    schema_version: int = SCHEMA_VERSION


class StageError(BaseModel):
    code: str                # machine-readable, e.g. "INVALID_JSON", "REF_DEPTH"
    detail: str              # human-readable
    where: str | None = None # endpoint / scenario id, if applicable


# ── SUBSTRATE ─────────────────────────────────────────────────────────────
class ReasoningRequest(BaseModel):
    task: str
    output_schema: dict | None = None
    capability_tier: str
    max_cost: float = 0.0
    max_latency: int = 0
    sensitivity: str = "standard"


class ReasoningResult(BaseModel):
    content: str | dict
    provider: str
    model: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    cached: bool = False
    schema_version: int = SCHEMA_VERSION


# ── INGEST ────────────────────────────────────────────────────────────────
class Mutation(BaseModel):
    """Deterministic, built in Stage 0. PLAN selects by id; it never invents these."""
    id: str                            # "omit_email", "email_too_long"
    case_type: str                     # "validation" | "happy_path" | "auth"
    expected_status: int
    instruction: str                   # given verbatim to the generator
    value: object | None = None


class EndpointSlice(BaseModel):
    path: str
    method: str                        # "GET" | "POST" | ...
    operation: dict                    # the OpenAPI operation object
    schemas: dict = Field(default_factory=dict)  # depth-limited resolved refs
    richness: float = 0.0              # 0.0–1.0
    mutations: list[Mutation] = Field(default_factory=list)  # may be [] (GET) -> happy/auth


class IngestOutput(BaseModel):
    endpoints: list[EndpointSlice]
    client_stub_path: str              # openapi-fetch client (Delta D1)
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta


# ── PLAN ──────────────────────────────────────────────────────────────────
class Scenario(BaseModel):
    endpoint: str
    method: str
    case_type: str
    priority: str = "P2"               # P1 | P2 | P3
    mutation_id: str | None = None     # SELECTED from the menu, never invented
    expected_status: int


class PlanOutput(BaseModel):
    scenarios: list[Scenario]
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta


# ── GENERATE ──────────────────────────────────────────────────────────────
class GenerateOutput(BaseModel):
    scenario_id: str
    test_code: str
    imports: list[str] = Field(default_factory=list)
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta


# ── REVIEW ────────────────────────────────────────────────────────────────
class GateResult(BaseModel):
    gate: str                          # "syntax" | "structure" | "ast" | ...
    passed: bool
    detail: str = ""


class Verdict(str, Enum):
    AUTO_APPROVE = "auto_approve"
    HITL = "hitl"                      # → the human review queue (the HITL feature)
    REGENERATE = "regenerate"


class ReviewOutput(BaseModel):
    scenario_id: str
    gates: list[GateResult]
    quality_score: float
    verdict: Verdict
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta


# ════════════════════════════════════════════════════════════════════════════
# B1 VISUAL REGRESSION — optional capability layer (Track B build-over)
# Reuses Track A Verdict/Status/StageMeta/StageError. Never replaces Track A.
# ════════════════════════════════════════════════════════════════════════════

class VisualSlice(BaseModel):
    """A single visual target: a URL rendered at a specific viewport."""
    name: str
    url: str
    viewport_w: int = 1280
    viewport_h: int = 800


class VisualScenario(BaseModel):
    """A planned visual check binding a slice to a baseline + tolerance."""
    slice_id: str
    baseline_path: str
    threshold_pixels: int = 100


class VisualGateResult(BaseModel):
    """One gate verdict on a visual comparison."""
    gate: str                              # e.g. 'pixel_diff'
    passed: bool
    diff_pixels: int = 0
    baseline_path: str = ''
    actual_path: str = ''


class VisualReport(BaseModel):
    """VisualStage output: one report per slice processed."""
    scenario_id: str
    gates: list[VisualGateResult]
    verdict: Verdict
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta


# ════════════════════════════════════════════════════════════════════════════
# B2 PERF BASELINES — optional capability layer (Track B build-over)
# Reuses Track A Verdict/Status/StageMeta/StageError. Never replaces Track A.
# Records run latencies in local SQLite (.cherenkov/perf_metrics.db) and flags
# statistical-outlier regressions vs historical mean+stddev (>= 3 runs).
# ════════════════════════════════════════════════════════════════════════════

class PerfSlice(BaseModel):
    """A single perf target: endpoint+method on a base URL with a load profile."""
    name: str
    target_url: str
    endpoint: str = "/"
    method: str = "GET"
    vus: int = 5
    duration_sec: int = 5


class PerfScenario(BaseModel):
    """A planned perf check binding a slice to a baseline metrics table."""
    slice_id: str
    baseline_db_path: str = ".cherenkov/perf_metrics.db"


class PerfGateResult(BaseModel):
    """One gate verdict on a perf measurement."""
    gate: str                              # e.g. latency_baseline
    passed: bool
    latency_ms: float = 0.0
    baseline_count: int = 0
    baseline_mean_ms: float = 0.0
    baseline_stddev_ms: float = 0.0
    threshold_limit_ms: float = 0.0
    anomaly_detected: bool = False
    k6_available: bool = True


class PerfReport(BaseModel):
    """PerfStage output: one report per slice processed."""
    scenario_id: str
    gates: list[PerfGateResult]
    verdict: Verdict
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta


# ════════════════════════════════════════════════════════════════════════════
# E3 DIVERGENCE ENGINE — Epoch 3 contracts (L2)
# Skeptic emits DivergenceHypothesis; Witness emits ReproductionResult;
# confirmed divergences are sealed into a DivergenceReport.
# ════════════════════════════════════════════════════════════════════════════

class DivergenceClass(str, Enum):
    """The five-way divergence space (see docs/vision/01_ARCHITECTURE.md §6)."""
    D1_SPEC_CODE = "D1_spec_code"   # spec says X, code accepts/returns Y
    D2_CODE_PROD = "D2_code_prod"   # code does X, prod silently returns Y
    D3_UI_SPEC   = "D3_ui_spec"     # UI/client sends X, spec expects Y
    D4_DB_CODE   = "D4_db_code"     # DB constraint vs code enforcement gap
    D5_SPEC_PROD = "D5_spec_prod"   # spec defines endpoint/shape, prod doesn't


class Severity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class DivergenceHypothesis(BaseModel):
    """A single testable claim that two sources disagree. Emitted by the Skeptic."""
    id: str
    divergence_class: DivergenceClass
    claim_a: str                              # what source A asserts
    claim_b: str                              # what source B likely does instead
    predicted_evidence: str                   # observable signal if divergence exists
    severity: Severity
    endpoint: str | None = None               # "{METHOD} {path}" or None
    repro_steps: list[str] = Field(default_factory=list)


class DivergenceEvidence(BaseModel):
    """Raw evidence captured by the Witness during a reproduction attempt."""
    request_summary: str                      # "{METHOD} {url} → {status} ({ms}ms)"
    response_actual: str | dict               # real response body or text
    response_expected: str | dict             # what the spec/claim_b predicted
    diff: str                                 # human-readable delta


class ReproductionResult(BaseModel):
    """Outcome of one Witness reproduction attempt. Independent of the Skeptic."""
    hypothesis_id: str
    reproduced: bool
    evidence: DivergenceEvidence | None = None
    rejection_reason: str | None = None


class DivergenceReport(BaseModel):
    """
    Sealed artifact for a confirmed divergence.
    Contract: {claim_a, claim_b, evidence, repro_steps, severity} — typed, serialisable.
    """
    id: str
    divergence_class: DivergenceClass
    claim_a: str
    claim_b: str
    evidence: DivergenceEvidence
    repro_steps: list[str]
    severity: Severity
    endpoint: str | None = None
    status: Status = Status.OK
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta
    scope: Literal["intra", "cross"] = "intra"

    def render(self) -> str:
        """Human-readable summary."""
        lines = [
            f"[{self.severity.upper()}] {self.divergence_class.value}"
            f" — {self.endpoint or 'unknown endpoint'}",
            f"  Claim A : {self.claim_a}",
            f"  Claim B : {self.claim_b}",
            f"  Evidence: {self.evidence.request_summary}",
            f"  Diff    : {self.evidence.diff}",
            "  Repro:",
        ]
        for i, step in enumerate(self.repro_steps, 1):
            lines.append(f"    {i}. {step}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# E1-5 Response/prefix cache + cost & latency accounting contracts
# ════════════════════════════════════════════════════════════════════════════

class CacheStats(BaseModel):
    """Cache performance statistics for a run."""
    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    hit_ratio: float = 0.0


class CostEntry(BaseModel):
    """A single cost & latency record for one inference request."""
    model: str
    provider: str = "ollama"
    duration_ms: int = 0
    tokens: int = 0
    cost: float = 0.0
    cache_hit: bool = False


class AccountingReport(BaseModel):
    """Per-run cost and latency summary."""
    entries: list[CostEntry] = Field(default_factory=list)
    total_duration_ms: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    cache_stats: CacheStats = Field(default_factory=CacheStats)


# ════════════════════════════════════════════════════════════════════════════
# E7 REFLECTOR / VERDICT MEMORY — Epoch 7 contracts
# VerdictRecord persists every accept/reject/escaped-defect decision.
# Idiom captures per-system patterns that keep being confirmed.
# ════════════════════════════════════════════════════════════════════════════

class VerdictOutcome(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ESCAPED_DEFECT = "escaped_defect"


class VerdictRecord(BaseModel):
    """Persistent record of one accept/reject/escaped-defect decision."""
    id: str
    hypothesis_id: str
    outcome: VerdictOutcome
    divergence_class: DivergenceClass | None = None
    endpoint: str | None = None
    failure_class: str | None = None
    source: str = "skeptic"          # "skeptic" | "healing" | "human"
    detail: str = ""
    timestamp: int = 0
    schema_version: int = SCHEMA_VERSION


class Idiom(BaseModel):
    """Per-system pattern that keeps being confirmed by verdicts.
    Decay score falls toward 0 over time; re-confirmation resets it.
    """
    id: str
    pattern: str
    divergence_class: DivergenceClass
    endpoint: str | None = None
    confirm_count: int = 1
    last_confirmed: int = 0
    decay_score: float = 1.0
    schema_version: int = SCHEMA_VERSION


class ReflectorConfig(BaseModel):
    """Configuration for the Reflector module."""
    enabled: bool = True
    store_path: str = ".cherenkov/verdicts.db"
    decay_half_life_hours: float = 168.0  # 7 days


# ── TRUTH MODEL / SOURCE ADAPTER SPI ──────────────────────────────────────────

class ProvenanceType(str, Enum):
    SPEC = "spec"
    CODE = "code"
    TRAFFIC = "traffic"
    DB = "db"


class Provenance(BaseModel):
    source_type: ProvenanceType
    source_uri: str
    details: dict = Field(default_factory=dict)


class Claim(BaseModel):
    id: str
    category: str  # e.g., "endpoint" | "request" | "response" | "mutation"
    subject: str   # e.g., "POST /users" | "POST /users -> body -> email"
    value: dict | str | list | None = None
    provenance: Provenance
    schema_version: int = SCHEMA_VERSION

