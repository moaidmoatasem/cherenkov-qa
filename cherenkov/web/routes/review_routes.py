"""FastAPI routes for HITL review queue management (approve, reject, edit, classify)."""
from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role
from cherenkov.web.routes.deps import _validate_scenario_id, get_queue, verify_api_key
from cherenkov.web.routes.models import ClassifyPayload, ReviewActionPayload

router = APIRouter(tags=["review"])


@router.get("/api/v1/review/queue")
async def list_review_queue(status: str | None = "pending", _auth=Depends(verify_api_key)):
    """List pending or filtered human-in-the-loop review queue items.

    Args:
        status: Optional status filter string ('pending', 'approved', 'rejected', or 'all').
        _auth: API key dependency.

    Returns:
        List of review item dictionaries including scenario ID, confidence, and generated test code.
    """
    queue = get_queue()
    query_status = None if status == "all" else status
    items = queue.list(status=query_status)
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))

    def _load_all_codes():
        codes = {}
        for item in items:
            spec_path = os.path.join(tests_dir, f"{item.id}.spec.ts")
            try:
                with open(spec_path, encoding="utf-8") as f:
                    codes[item.id] = f.read() or None
            except OSError:
                codes[item.id] = None
        return codes

    codes = await asyncio.to_thread(_load_all_codes)
    return [
        {
            "id": item.id,
            "endpoint": item.endpoint,
            "method": item.method,
            "confidence": item.confidence,
            "confidence_reason": item.confidence_reason,
            "review_gate_failed": item.review_gate_failed,
            "status": item.status.value,
            "reject_reason": item.reject_reason,
            "generated_test": codes.get(item.id),
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.post("/api/v1/review/approve")
async def approve_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key), _role=Depends(require_role(Role.reviewer))):
    """Approve a review queue item and feed the positive verdict to Reflector.

    Args:
        payload: ReviewActionPayload containing scenario_id and optional reason.
        _auth: API key dependency.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary confirming approval status and scenario_id.

    Raises:
        HTTPException: 404 if item not found, or 409 if status conflict occurs.
    """
    from cherenkov.core.feedback_store import FeedbackEntry, FeedbackStore

    queue = get_queue()
    actor = os.environ.get("USER", "dashboard")
    envelope = queue.approve(payload.scenario_id, actor=actor, source="web")
    if not envelope.ok:
        raise HTTPException(
            status_code=409 if envelope.error and envelope.error.code == "conflict" else 404,
            detail=envelope.error.message if envelope.error else "approve failed",
        )
    store = FeedbackStore()
    store.record_feedback(
        FeedbackEntry(hitl_item_id=payload.scenario_id, action="approve", reason=payload.reason or "Approved by reviewer")
    )
    try:
        from cherenkov.core.contracts import VerdictOutcome
        from cherenkov.reflector.reflector import Reflector
        reflector = Reflector(run_id="web")
        reflector.ingest_human_verdict(
            hypothesis_id=payload.scenario_id, outcome=VerdictOutcome.ACCEPT,
            detail=payload.reason or "Approved via review dashboard",
        )
    except Exception as e:
        logging.getLogger("HITL").warning("failed to feed approve verdict to Reflector", exc_info=e)
    return {"status": "approved", "scenario_id": payload.scenario_id}


@router.post("/api/v1/review/reject")
async def reject_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key), _role=Depends(require_role(Role.reviewer))):
    """Reject a review queue item and record the rejection reason.

    Args:
        payload: ReviewActionPayload containing scenario_id, reason, and optional note.
        _auth: API key dependency.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary confirming rejection status and scenario_id.

    Raises:
        HTTPException: 404 if item not found, or 409 if status conflict occurs.
    """
    from cherenkov.core.feedback_store import FeedbackEntry, FeedbackStore

    queue = get_queue()
    actor = os.environ.get("USER", "dashboard")
    category = payload.reason or "other"
    stored_reason = f"{category}: {payload.note}" if payload.note else category
    envelope = queue.reject(payload.scenario_id, actor=actor, reason=stored_reason, source="web")
    if not envelope.ok:
        raise HTTPException(
            status_code=409 if envelope.error and envelope.error.code == "conflict" else 404,
            detail=envelope.error.message if envelope.error else "reject failed",
        )
    store = FeedbackStore()
    store.record_feedback(
        FeedbackEntry(hitl_item_id=payload.scenario_id, action="reject", reason=category, notes=payload.note)
    )
    try:
        from cherenkov.core.contracts import VerdictOutcome
        from cherenkov.reflector.reflector import Reflector
        reflector = Reflector(run_id="web")
        reflector.ingest_human_verdict(
            hypothesis_id=payload.scenario_id, outcome=VerdictOutcome.REJECT, detail=stored_reason,
        )
    except Exception as e:
        logging.getLogger("HITL").warning("failed to feed reject verdict to Reflector", exc_info=e)
    return {"status": "rejected", "scenario_id": payload.scenario_id}


@router.post("/api/v1/review/edit")
async def edit_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key), _role=Depends(require_role(Role.reviewer))):
    """Save user-edited test code for a specific review scenario.

    Args:
        payload: ReviewActionPayload containing scenario_id and updated test_code.
        _auth: API key dependency.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary confirming saved status and scenario_id.

    Raises:
        HTTPException: 400 Bad Request if test_code is missing.
    """
    if not payload.test_code:
        raise HTTPException(status_code=400, detail="Missing updated test code content.")
    _validate_scenario_id(payload.scenario_id)
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    os.makedirs(tests_dir, exist_ok=True)
    file_path = os.path.join(tests_dir, f"{payload.scenario_id}.spec.ts")
    code_to_write = payload.test_code

    def _write():
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(code_to_write)

    await asyncio.to_thread(_write)
    return {"status": "saved", "scenario_id": payload.scenario_id}


@router.post("/api/v1/review/classify")
async def classify_review_item(payload: ClassifyPayload, _auth=Depends(verify_api_key), _role=Depends(require_role(Role.reviewer))):
    """Classify a review item as regression, intended, or ignore.

    Args:
        payload: ClassifyPayload containing item_id, classification, and optional detail.
        _auth: API key dependency.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary confirming classification outcome.

    Raises:
        HTTPException: 400 for unknown classification, 404/409 on queue operation failure.
    """
    queue = get_queue()
    actor = payload.actor or os.environ.get("USER", "dashboard")
    if payload.classification == "regression":
        envelope = queue.approve(payload.item_id, actor=actor, source="web")
    elif payload.classification == "intended":
        envelope = queue.reject(payload.item_id, actor=actor, reason=payload.detail or "classified as intended", source="web")
    elif payload.classification == "ignore":
        envelope = queue.ignore(payload.item_id, actor, source="web")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown classification: {payload.classification}")
    if not envelope.ok:
        raise HTTPException(
            status_code=409 if envelope.error and envelope.error.code == "conflict" else 404,
            detail=envelope.error.message if envelope.error else "classify failed",
        )
    return {"status": "classified", "item_id": payload.item_id, "classification": payload.classification}
