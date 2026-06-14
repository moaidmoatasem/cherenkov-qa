"""
cherenkov/validate/contracts.py
Pydantic v2 result-contract models for the Validation Gate.

schema_version = 'validate/v1'
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GateCriteria(BaseModel):
    """Declares a single gate check and whether it is required for a 'pass' result."""

    name: str
    description: str
    required: bool = True


class GateEvidence(BaseModel):
    """Records the outcome of a single gate check after execution."""

    gate: str
    passed: bool
    detail: str
    evidence_ref: str | None = None  # absolute or relative path to captured output file


class ValidationReport(BaseModel):
    """Full validation run report.

    result semantics
    ----------------
    pass      – all *required* gates passed (optional may fail)
    degraded  – all required passed, at least one *optional* gate failed
    fail      – at least one *required* gate failed
    """

    schema_version: str = Field(default="validate/v1")
    run_id: str
    timestamp: str
    result: Literal["pass", "fail", "degraded"]
    gates: list[GateEvidence]
    summary: str
    evidence_dir: str | None = None
