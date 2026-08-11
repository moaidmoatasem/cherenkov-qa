"""Teleport REST Routes (CC-5)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from cherenkov.continuity.sessions.adapters.sqlite_sessions import SQLiteSessionStore
from cherenkov.continuity.sessions.use_cases.resume import ResumeSessionUseCase

router = APIRouter(prefix="/api/v1/teleport", tags=["teleport"])
store = SQLiteSessionStore()
resume_uc = ResumeSessionUseCase(store)


@router.get("/qr")
def get_teleport_qr(token: str) -> dict[str, Any]:
    """Retrieve session snapshot via QR token.

    Args:
        token: QR session token string.

    Returns:
        Dictionary payload containing status, session ID, and state data snapshot.

    Raises:
        HTTPException: 404 Not Found if token is invalid or expired.
    """
    snapshot = resume_uc.execute_by_token(token)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Token not found or expired")

    return {
        "status": "success",
        "session_id": snapshot.id,
        "state_data": snapshot.state_data
    }
