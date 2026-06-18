from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from cherenkov.web.routes.deps import (
    verify_api_key,
    _validate_spec_url,
    _validate_output_path,
    ws_event_callback,
)
from cherenkov.web.routes.models import (
    RunPipelinePayload,
    ValidatePayload,
    EjectPayload,
)

router = APIRouter(tags=["operations"])


@router.post("/api/v1/ingest")
async def ingest_spec_file(
    file: UploadFile | None = File(None), url: str | None = Form(None)
):
    import os
    import uuid
    import asyncio
    from cherenkov.stages.ingest import IngestStage

    run_id = str(uuid.uuid4())[:8]
    temp_dir = os.path.abspath(os.path.join(os.getcwd(), ".cherenkov/temp_ingest"))
    os.makedirs(temp_dir, exist_ok=True)
    spec_path = os.path.join(
        temp_dir,
        f"spec_{run_id}.json"
        if (file and file.filename and file.filename.endswith(".json"))
        else f"spec_{run_id}.yaml",
    )
    if not file and not url:
        raise HTTPException(
            status_code=400, detail="Either file upload or URL must be provided."
        )
    try:
        if file:
            MAX_SPEC_BYTES = 10 * 1024 * 1024
            content = await file.read(MAX_SPEC_BYTES + 1)
            if len(content) > MAX_SPEC_BYTES:
                raise HTTPException(
                    status_code=413, detail="Spec file exceeds 10MB limit"
                )
            with open(spec_path, "wb") as f:
                f.write(content)
        elif url:
            import requests

            safe_url = await _validate_spec_url(url)
            resp = await asyncio.to_thread(requests.get, safe_url, timeout=15)
            resp.raise_for_status()
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
        ingest_stage = IngestStage(run_id)
        ingest_output = await asyncio.to_thread(ingest_stage.run, spec_path)
        endpoints = []
        for ep in ingest_output.endpoints:
            missing = []
            for m in ep.mutations or []:
                if hasattr(m, "instruction") and m.instruction:
                    missing.append(m.instruction)
            endpoints.append(
                {
                    "path": ep.path,
                    "method": ep.method,
                    "richness": ep.richness,
                    "missing_elements": missing,
                }
            )
        return {
            "spec_path": spec_path,
            "endpoints": endpoints,
            "richness": sum(ep["richness"] for ep in endpoints) / len(endpoints)  # type: ignore
            if endpoints
            else 0.0,
        }
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(spec_path):
            os.remove(spec_path)
        raise HTTPException(
            status_code=500,
            detail="Spec parsing failed. Check that the file is a valid OpenAPI 3.x document.",
        )


def _run_pipeline_thread(spec_path: str, run_id: str):
    from cherenkov.core.orchestrator import OrchestrationEngine

    try:
        engine = OrchestrationEngine(run_id=run_id, event_callback=ws_event_callback)
        engine.run_pipeline(spec_path)
    except Exception as e:
        ws_event_callback("pipeline_error", {"detail": str(e)})


@router.post("/api/v1/run")
async def trigger_pipeline_run(
    payload: RunPipelinePayload,
    background_tasks: BackgroundTasks,
    _auth=Depends(verify_api_key),
):
    import os
    import uuid
    import threading
    import io
    import contextlib as _contextlib
    from cherenkov.stages.doctor_cmd import run_doctor

    with _contextlib.redirect_stdout(io.StringIO()):
        doctor_status = run_doctor()
    if payload.demo_mode:
        from cherenkov.execution.demo_mode import generate_demo_findings

        generate_demo_findings()
        return {"run_id": "demo", "status": "demo_completed"}
    if doctor_status != 0:
        print("Warning: Doctor preflight checks reported issues. Continuing anyway.")
    run_id = str(uuid.uuid4())[:8]
    if not os.path.exists(payload.spec_path):
        raise HTTPException(
            status_code=404, detail="Ingested spec file path not found."
        )
    thread = threading.Thread(
        target=_run_pipeline_thread, args=(payload.spec_path, run_id)
    )
    thread.daemon = True
    thread.start()
    return {"run_id": run_id, "status": "launched"}


@router.get("/api/v1/tests")
async def list_generated_tests():
    import os
    import asyncio
    import re as _re

    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    if not os.path.exists(tests_dir):
        return []

    def _scan():
        tests = []
        for f in sorted(os.listdir(tests_dir)):
            if not f.endswith(".spec.ts"):
                continue
            file_path = os.path.join(tests_dir, f)
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    code = fh.read()
            except OSError:
                continue
            if not code or not code.strip():
                continue
            scenario_id = f.replace(".spec.ts", "")
            method_match = _re.search(
                r'method:\s*["\']([A-Z]+)["\']', code
            ) or _re.search(r"\.(get|post|put|patch|delete)\s*\(", code, _re.IGNORECASE)
            method = method_match.group(1).upper() if method_match else "GET"
            tests.append(
                {
                    "name": f,
                    "scenario_id": scenario_id,
                    "endpoint": scenario_id,
                    "method": method,
                    "code": code,
                }
            )
        return tests

    return await asyncio.to_thread(_scan)


@router.post("/api/v1/validate")
async def validate_test_suite(payload: ValidatePayload, _auth=Depends(verify_api_key)):
    import asyncio
    from cherenkov.execution.validate import ValidationEngine

    await _validate_spec_url(payload.target_url)
    try:
        engine = ValidationEngine("api_validate")
        results = await asyncio.wait_for(
            asyncio.to_thread(engine.validate_suite, payload.target_url),
            timeout=300.0,
        )
        return results
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="Validation timed out after 300 seconds."
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Validation failed. Check the target URL and try again.",
        )


@router.post("/api/v1/eject")
async def eject_test_suite(payload: EjectPayload, _auth=Depends(verify_api_key)):
    import os

    try:
        safe_path = _validate_output_path(payload.output_path)
        from cherenkov.execution.eject import EjectorEngine

        engine = EjectorEngine("api_eject")
        success = engine.eject_suite(safe_path)
        if not success:
            raise HTTPException(status_code=500, detail="Ejection failed.")
        files = []
        for root, _dirs, fnames in os.walk(safe_path):
            for f in fnames:
                rel_dir = os.path.relpath(root, safe_path)
                files.append(os.path.join(rel_dir, f).replace("\\", "/"))
        return {"status": "ejected", "output_path": safe_path, "files": files}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eject operation failed: {e}")
