"""FastAPI routes for querying and acting on API specification divergences."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from cherenkov.execution.failure_classifier import classify_failure
from cherenkov.web import divergences as divergence_store
from cherenkov.web.routes.deps import verify_api_key

router = APIRouter(tags=["divergences"])


class DivergenceActionPayload(BaseModel):
    """Payload for performing an action (e.g. acknowledge/ignore) on a divergence."""
    divergence_id: str
    action: str
    reason: str | None = None


class ClassifyFailurePayload(BaseModel):
    """Payload for classifying an endpoint failure pattern."""
    endpoint: str
    method: str = "GET"


@router.get("/api/v1/divergences")
async def list_divergences():
    """List all detected API spec divergences.

    Returns:
        List of divergence dictionaries.
    """
    return divergence_store.list_divergences()


@router.post("/api/v1/divergences/classify-failure")
async def classify_failure_route(payload: ClassifyFailurePayload):
    """Classify an endpoint failure into a failure category.

    Args:
        payload: ClassifyFailurePayload object.

    Returns:
        Classification result model dump dictionary.
    """
    result = classify_failure(payload.endpoint, payload.method)
    return result.model_dump()


@router.post("/api/v1/divergences/act")
async def act_on_divergence(payload: DivergenceActionPayload, _auth=Depends(verify_api_key)):
    """Apply an action to a specified divergence finding.

    Args:
        payload: DivergenceActionPayload object.
        _auth: API key dependency.

    Returns:
        Dictionary summarizing action execution and updated status.

    Raises:
        HTTPException: 400 if action is unknown, or 404 if divergence_id is not found.
    """
    try:
        new_status = divergence_store.apply_action(payload.divergence_id, payload.action)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown divergence id: {payload.divergence_id}") from None
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}") from None
    return {
        "status": "ok",
        "divergence_id": payload.divergence_id,
        "action": payload.action,
        "new_status": new_status,
    }
