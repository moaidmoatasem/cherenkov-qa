"""Shared Pydantic models for web API route modules."""
from __future__ import annotations

from pydantic import BaseModel


class RunPipelinePayload(BaseModel):
    """Payload model for triggering a pipeline execution run."""
    spec_path: str
    target_url: str | None = None
    auth_header: str | None = None
    demo_mode: bool = False
    intent: str | None = None


class ReviewActionPayload(BaseModel):
    """Payload model for review actions (approve, reject, edit) on triage items."""
    scenario_id: str
    reason: str | None = None
    note: str | None = None
    test_code: str | None = None


class ValidatePayload(BaseModel):
    """Payload model for validating test suites against a target URL."""
    target_url: str


class EjectPayload(BaseModel):
    """Payload model for ejecting test suites into standalone runnable files."""
    output_path: str


class ClassifyPayload(BaseModel):
    """Payload model for updating triage item classification."""
    item_id: str
    classification: str
    detail: str | None = None
    actor: str | None = None
