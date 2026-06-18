from fastapi import APIRouter, Depends, HTTPException

from cherenkov.web.routes.deps import get_queue, verify_api_key, _validate_scenario_id
from cherenkov.web.routes.models import ReviewActionPayload, ClassifyPayload

router = APIRouter(tags=["review"])


@router.get("/api/v1/review/queue")
async def list_review_queue(status: str | None = "pending", _auth=Depends(verify_api_key)):
    import os
    import asyncio
    queue = get_queue()
    items = queue.list(status=status)
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
            "generated_test": codes.get(item.id),
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.post("/api/v1/review/approve")
async def approve_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    import os
    from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry

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
        from cherenkov.reflector.reflector import Reflector
        from cherenkov.core.contracts import VerdictOutcome
        reflector = Reflector(run_id="web")
        reflector.ingest_human_verdict(
            hypothesis_id=payload.scenario_id, outcome=VerdictOutcome.ACCEPT,
            detail=payload.reason or "Approved via review dashboard",
        )
    except Exception as e:
        import logging
        logging.getLogger("HITL").warning("failed to feed approve verdict to Reflector", exc_info=e)
    return {"status": "approved", "scenario_id": payload.scenario_id}


@router.post("/api/v1/review/reject")
async def reject_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    import os
    from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry

    queue = get_queue()
    actor = os.environ.get("USER", "dashboard")
    reason = payload.reason or "Rejected by reviewer"
    envelope = queue.reject(payload.scenario_id, actor=actor, reason=reason, source="web")
    if not envelope.ok:
        raise HTTPException(
            status_code=409 if envelope.error and envelope.error.code == "conflict" else 404,
            detail=envelope.error.message if envelope.error else "reject failed",
        )
    store = FeedbackStore()
    store.record_feedback(FeedbackEntry(hitl_item_id=payload.scenario_id, action="reject", reason=reason))
    try:
        from cherenkov.reflector.reflector import Reflector
        from cherenkov.core.contracts import VerdictOutcome
        reflector = Reflector(run_id="web")
        reflector.ingest_human_verdict(
            hypothesis_id=payload.scenario_id, outcome=VerdictOutcome.REJECT, detail=reason,
        )
    except Exception as e:
        import logging
        logging.getLogger("HITL").warning("failed to feed reject verdict to Reflector", exc_info=e)
    return {"status": "rejected", "scenario_id": payload.scenario_id}


@router.post("/api/v1/review/edit")
async def edit_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    import os
    import asyncio
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
async def classify_review_item(payload: ClassifyPayload, _auth=Depends(verify_api_key)):
    import os
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
