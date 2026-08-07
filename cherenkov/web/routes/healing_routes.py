"""Suggest-only healing suggestions over stored verdicts.

D7 invariant: this endpoint produces a human-readable suggestion only. It never
applies, never writes a test file, and never reports a write it did not do.
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cherenkov.web.routes.deps import verify_api_key

_log = logging.getLogger(__name__)

router = APIRouter(tags=["healing"])


class HealingSuggestionPayload(BaseModel):
    verdict_id: str


def _load_verdict(verdict_id: str) -> dict | None:
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()
    try:
        conn = sqlite3.connect(store.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT id, hypothesis_id, outcome, failure_class, endpoint, detail, timestamp "
                "FROM verdicts WHERE id = ?",
                (verdict_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        _log.error("failed to load verdict %s", verdict_id, exc_info=True)
        return None


def _generic_suggestion(endpoint: str, failure_class: str, detail: str) -> str:
    return "\n".join(
        [
            "",
            "=" * 70,
            "  [HEALING SUGGESTION] - REVIEW FAILURE (suggest-only)",
            "=" * 70,
            f"Endpoint: {endpoint}",
            f"Failure class: {failure_class}",
            f"Diagnosis: {detail or 'Failure detected during review.'}",
            "",
            "SUGGESTED ACTIONS (never auto-applied):",
            "1. Inspect the observed payload in the Spec vs Reality diff viewer.",
            "2. Decide whether the API or the test assertion is wrong.",
            "3. Approve or reject the failure in the review queue; the verdict teaches CHERENKOV.",
            "4. If the API changed intentionally, update the spec; if the test drifted, regenerate.",
            "=" * 70,
        ]
    )


@router.post("/api/v1/healing/suggestions")
async def healing_suggestion(
    payload: HealingSuggestionPayload, _auth=Depends(verify_api_key)
):
    verdict = _load_verdict(payload.verdict_id)
    if verdict is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown verdict id: {payload.verdict_id}"
        )

    endpoint = verdict.get("endpoint") or payload.verdict_id
    failure_class = (verdict.get("failure_class") or "UNKNOWN").upper()
    detail = verdict.get("detail") or ""
    note = ""

    if failure_class == "AUTH_EXPIRY":
        from cherenkov.healing.auth_expiry import AuthExpiryHealer

        result = AuthExpiryHealer().suggest_heal(payload.verdict_id, endpoint)
        suggestion = result["suggestion"]
        healer = "AuthExpiryHealer"
    elif failure_class == "CONTRACT_DRIFT":
        from cherenkov.healing.contract_drift import ContractDriftHealer

        healer = "ContractDriftHealer"
        suggestion = _generic_suggestion(endpoint, failure_class, detail)
        note = (
            "Full ContractDriftHealer field diffing needs the captured missing/added "
            "field lists, which are not stored per verdict."
        )
    else:
        healer = "GenericHealer"
        suggestion = _generic_suggestion(endpoint, failure_class, detail)

    return {
        "verdict_id": payload.verdict_id,
        "endpoint": endpoint,
        "failure_class": failure_class,
        "diagnosis": detail,
        "healer": healer,
        "suggestion": suggestion,
        "healed": False,
        "note": note,
    }
