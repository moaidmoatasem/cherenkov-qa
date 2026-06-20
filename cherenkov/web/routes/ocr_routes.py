from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cherenkov.review_ocr.stage import ReviewStageOCR
from cherenkov.core.settings import get_settings

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


class OcrReviewPayload(BaseModel):
    code: str


@router.get("/status")
async def ocr_status():
    try:
        stage = ReviewStageOCR()
        installed = stage._check_ocr_installed()
        binary = stage._get_ocr_binary()
    except Exception as e:
        return {"installed": False, "binary": "ocr", "version": "", "error": str(e)}
    import subprocess
    version = ""
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=5)
        version = (result.stdout or result.stderr).strip()
    except Exception:
        pass
    return {
        "installed": installed,
        "binary": binary,
        "version": version,
        "error": "",
    }


@router.post("/review/{scenario_id}")
async def run_ocr_review(scenario_id: str, payload: OcrReviewPayload):
    if not get_settings().OCR_ENABLED:
        raise HTTPException(status_code=400, detail="OCR review is not enabled. Set CHERENKOV_OCR_ENABLED=true")
    stage = ReviewStageOCR(run_id=scenario_id)
    import os
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
async def get_ocr_review(scenario_id: str):
    raise HTTPException(status_code=404, detail="No cached OCR review available. POST to run a review.")
