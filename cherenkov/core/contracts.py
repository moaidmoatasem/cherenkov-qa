"""
CHERENKOV core/contracts.py — the typed boundaries between every pipeline stage.
Authority: v3.1 + delta. These are the Pydantic contracts the whole DAG enforces.

A stage that emits data failing its contract fails LOUDLY here, at the boundary,
instead of silently corrupting the next stage. Versioned so a model/prompt change
can't quietly break a downstream consumer.
"""
from __future__ import annotations

from enum import Enum
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
