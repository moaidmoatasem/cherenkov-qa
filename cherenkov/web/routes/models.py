"""Shared Pydantic models for web API route modules."""

from pydantic import BaseModel


class RunPipelinePayload(BaseModel):
    spec_path: str
    target_url: str | None = None
    auth_header: str | None = None
    demo_mode: bool = False
    intent: str | None = None


class ReviewActionPayload(BaseModel):
    scenario_id: str
    reason: str | None = None
    test_code: str | None = None


class ValidatePayload(BaseModel):
    target_url: str


class EjectPayload(BaseModel):
    output_path: str


class ClassifyPayload(BaseModel):
    item_id: str
    classification: str
    detail: str | None = None
    actor: str | None = None
