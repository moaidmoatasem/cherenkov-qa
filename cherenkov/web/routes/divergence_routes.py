from fastapi import APIRouter, Depends
from pydantic import BaseModel

from cherenkov.web import divergences as divergence_store
from cherenkov.web.routes.deps import verify_api_key

router = APIRouter(tags=["divergences"])


class DivergenceActionPayload(BaseModel):
    divergence_id: str
    action: str
    reason: str | None = None


@router.get("/api/v1/divergences")
async def list_divergences():
    return divergence_store.list_divergences()


@router.post("/api/v1/divergences/act")
async def act_on_divergence(payload: DivergenceActionPayload, _auth=Depends(verify_api_key)):
    try:
        new_status = divergence_store.apply_action(payload.divergence_id, payload.action)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown divergence id: {payload.divergence_id}")
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")
    return {
        "status": "ok",
        "divergence_id": payload.divergence_id,
        "action": payload.action,
        "new_status": new_status,
    }
