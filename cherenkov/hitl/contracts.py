"""
CHERENKOV hitl/contracts.py — the frozen `hitl/v1` integration seam.

This is the persistence + envelope layer the OpenClaw spec assumes already
exists. It does NOT yet — this module builds it as Track-A scope (it
operationalizes the existing `Verdict.HITL` from REVIEW). Voice layers (OpenClaw,
dashboard) consume ONLY the JSON envelope; they never touch the DB.

Versioned Pydantic seam (companion to core/contracts.py), kept local to the hitl
package so it never forks the hot core contracts file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "hitl/v1"

# Frozen error-code vocabulary (Appendix A).
ERROR_CODES = frozenset(
    {
        "conflict",
        "not_found",
        "forbidden",
        "invalid_input",
        "db_locked",
        "llm_unavailable",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HitlStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IGNORED = "ignored"


class HitlItem(BaseModel):
    """One human-review item. Bridges REVIEW's `Verdict.HITL` into a durable,
    addressable queue entry with a state machine."""

    id: str
    status: HitlStatus = HitlStatus.PENDING
    endpoint: str | None = None
    method: str | None = None
    mutation_id: str | None = None
    mutation_label: str | None = None
    confidence: float | None = None
    confidence_reason: str | None = None
    review_gate_failed: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    reject_reason: str | None = None
    run_id: str | None = None
    spec_hash: str | None = None
    created_at: str = Field(default_factory=_now_iso)


class HitlError(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class HitlEnvelope(BaseModel):
    """The only thing voice layers parse. Stable across hitl/v1."""

    schema_version: str = SCHEMA_VERSION
    ok: bool
    command: str
    payload: Any | None = None
    error: HitlError | None = None


def ok_envelope(command: str, payload: Any) -> HitlEnvelope:
    return HitlEnvelope(ok=True, command=command, payload=payload, error=None)


def err_envelope(
    command: str, code: str, message: str, detail: dict | None = None
) -> HitlEnvelope:
    if code not in ERROR_CODES:
        raise ValueError(f"unknown hitl error code: {code}")
    return HitlEnvelope(
        ok=False,
        command=command,
        payload=None,
        error=HitlError(code=code, message=message, detail=detail or {}),
    )
