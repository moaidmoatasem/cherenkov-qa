"""API route handlers for OpenClaw Reviewer (OCR) integration."""
from __future__ import annotations

import logging
import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_log = logging.getLogger(__name__)

from cherenkov.core.settings import get_settings
from cherenkov.review_ocr.stage import ReviewStageOCR
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role
from cherenkov.web.routes.deps import _validate_scenario_id

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


class OcrReviewPayload(BaseModel):
    """Payload model for executing OCR code review."""
    code: str


@router.get("/status")
async def ocr_status():
    """Check OCR tool installation and binary status.

    Returns:
        Dictionary payload containing installed boolean, binary path, and version string.
    """
    try:
        stage = ReviewStageOCR()
        installed = stage._check_ocr_installed()
        binary = stage._get_ocr_binary()
    except Exception as e:
        return {"installed": False, "binary": "ocr", "version": "", "error": str(e)}
    version = ""
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=5)
        version = (result.stdout or result.stderr).strip()
    except Exception:
        _log.debug("could not detect tool version", exc_info=True)
    return {
        "installed": installed,
        "binary": binary,
        "version": version,
        "error": "",
    }


@router.post("/review/{scenario_id}")
async def run_ocr_review(scenario_id: str, payload: OcrReviewPayload, _role=Depends(require_role(Role.reviewer))):
    """Run OCR code review on generated test code for a scenario.

    Args:
        scenario_id: Unique scenario identifier string.
        payload: OcrReviewPayload containing code string.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary payload listing findings, score deduction, and agent summary.

    Raises:
        HTTPException: 400 Bad Request if OCR is not enabled.
    """
    _validate_scenario_id(scenario_id)
    if not get_settings().OCR_ENABLED:
        raise HTTPException(status_code=400, detail="OCR review is not enabled. Set CHERENKOV_OCR_ENABLED=true")
    stage = ReviewStageOCR(run_id=scenario_id)
    filepath = os.path.join(os.getcwd(), "stub", "generated_tests", f"{scenario_id}.spec.ts")
    output = stage.run_on_file(filepath, payload.code)
    return {
        "passed": output.passed,
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "column": f.column,
                "severity": f.severity.value,
                "rule": f.rule,
                "message": f.message,
                "suggestion": f.suggestion,
            }
            for f in output.findings
        ],
        "score_deduction": output.score_deduction,
        "agent_summary": output.agent_summary,
        "llm_model": output.llm_model,
        "duration_ms": output.duration_ms,
        "error": output.error,
    }


@router.get("/review/{scenario_id}")
async def get_ocr_review(_scenario_id: str):
    """Retrieve cached OCR review results for a scenario.

    Args:
        _scenario_id: Target scenario identifier string.

    Raises:
        HTTPException: 404 Not Found (cache lookup fallback).
    """
    raise HTTPException(status_code=404, detail="No cached OCR review available. POST to run a review.")
