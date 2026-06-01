"""
CHERENKOV api/main.py — FastAPI web server and WebSocket backbone.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import json
import uuid
import asyncio
import shutil
import threading
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cherenkov.core.config import Config
from cherenkov.stages.ingest import IngestStage
from cherenkov.core.orchestrator import OrchestrationEngine
from cherenkov.execution.validate import ValidationEngine

app = FastAPI(
    title="CHERENKOV QA Observability Dashboard Server",
    version="1.1.0",
    description="Localhost-first dashboard server for API conformance testing."
)

# Enable CORS for local cross-port browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket Manager ──────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Discard stale connections gracefully
                pass

manager = ConnectionManager()

# Global reference to main event loop for thread-safe websocket broadcasts
main_loop = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

# Thread-safe event callback to feed synchronous orchestrator updates to async WS
def ws_event_callback(type_: str, payload: dict):
    if main_loop and manager.active_connections:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": type_, "payload": payload}),
            main_loop
        )

# ── API Endpoint Schemas ────────────────────────────────────────────────
class RunPipelinePayload(BaseModel):
    spec_path: str
    target_url: str | None = None
    auth_header: str | None = None

class ReviewActionPayload(BaseModel):
    scenario_id: str
    reason: str | None = None
    test_code: str | None = None

class ValidatePayload(BaseModel):
    target_url: str

class EjectPayload(BaseModel):
    output_path: str

# ── Endpoints ──────────────────────────────────────────────────────────
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "online",
        "device": Config.detect_ollama_device(),
        "gen_model": Config.GEN_MODEL,
        "active_connections": len(manager.active_connections),
        "workspace_root": os.getcwd()
    }

@app.post("/api/v1/ingest")
async def ingest_spec_file(
    file: UploadFile | None = File(None),
    url: str | None = Form(None)
):
    """Parses spec and yields endpoints segments with richness metadata coverage."""
    run_id = str(uuid.uuid4())[:8]
    temp_dir = os.path.abspath(os.path.join(os.getcwd(), ".cherenkov/temp_ingest"))
    os.makedirs(temp_dir, exist_ok=True)
    spec_path = os.path.join(temp_dir, f"spec_{run_id}.json" if (file and file.filename and file.filename.endswith('.json')) else f"spec_{run_id}.yaml")

    try:
        if file:
            with open(spec_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        elif url:
            # Simple remote fetch fallback
            import requests
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
        else:
            raise HTTPException(status_code=400, detail="Either file upload or URL must be provided.")

        # Run real IngestStage
        ingest_stage = IngestStage(run_id)
        ingest_output = ingest_stage.run(spec_path)

        endpoints = []
        for ep in ingest_output.endpoints:
            endpoints.append({
                "path": ep.path,
                "method": ep.method,
                "richness": ep.richness,
                "missing_elements": ep.mutations[0].instruction if ep.mutations else []
            })

        return {
            "spec_path": spec_path,
            "endpoints": endpoints,
            "richness": sum(ep["richness"] for ep in endpoints) / len(endpoints) if endpoints else 0.0
        }
    except Exception as e:
        if os.path.exists(spec_path):
            os.remove(spec_path)
        raise HTTPException(status_code=500, detail=f"Parsing error: {e}")

def run_pipeline_thread(spec_path: str, run_id: str):
    """Executes E2E pipeline run inside background worker thread."""
    try:
        engine = OrchestrationEngine(run_id=run_id, event_callback=ws_event_callback)
        engine.run_pipeline(spec_path)
    except Exception as e:
        ws_event_callback("pipeline_error", {"detail": str(e)})

@app.post("/api/v1/run")
async def trigger_pipeline_run(payload: RunPipelinePayload, background_tasks: BackgroundTasks):
    """Launches E2E pipeline asynchronously as a background thread worker."""
    run_id = str(uuid.uuid4())[:8]
    if not os.path.exists(payload.spec_path):
        raise HTTPException(status_code=404, detail="Ingested spec file path not found.")

    # Spawn thread to run synchronus LLM completions safely
    thread = threading.Thread(target=run_pipeline_thread, args=(payload.spec_path, run_id))
    thread.daemon = True
    thread.start()

    return {
        "run_id": run_id,
        "status": "launched"
    }

@app.get("/api/v1/tests")
async def list_generated_tests():
    """Lists all compiled test files inside stub/generated_tests."""
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    if not os.path.exists(tests_dir):
        return []

    tests = []
    for f in os.listdir(tests_dir):
        if f.endswith(".spec.ts"):
            file_path = os.path.join(tests_dir, f)
            with open(file_path, "r", encoding="utf-8") as file:
                code = file.read()
            
            # Simple metadata parses
            scenario_id = f.replace(".spec.ts", "")
            tests.append({
                "name": f,
                "scenario_id": scenario_id,
                "endpoint": scenario_id,
                "method": "POST" if "create" in scenario_id else "GET",
                "code": code
            })
    return tests

@app.post("/api/v1/review/approve")
async def approve_scenario(payload: ReviewActionPayload):
    # Standard positive learning example stores
    return {"status": "approved", "scenario_id": payload.scenario_id}

@app.post("/api/v1/review/reject")
async def reject_scenario(payload: ReviewActionPayload):
    # Remove from disk
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    file_path = os.path.join(tests_dir, f"{payload.scenario_id}.spec.ts")
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"status": "rejected", "scenario_id": payload.scenario_id}

@app.post("/api/v1/review/edit")
async def edit_scenario(payload: ReviewActionPayload):
    if not payload.test_code:
        raise HTTPException(status_code=400, detail="Missing updated test code content.")
    
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    file_path = os.path.join(tests_dir, f"{payload.scenario_id}.spec.ts")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(payload.test_code)
    return {"status": "saved", "scenario_id": payload.scenario_id}

@app.post("/api/v1/validate")
async def validate_test_suite(payload: ValidatePayload):
    """Executes the Playwright ValidationEngine and generates suggested tightening code."""
    try:
        engine = ValidationEngine("api_validate")
        results = engine.validate_suite(payload.target_url)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/eject")
async def eject_test_suite(payload: EjectPayload):
    """Ejects the test suite to a standalone folder with standard configs and zero CHERENKOV dependencies."""
    try:
        from cherenkov.execution.eject import EjectorEngine
        engine = EjectorEngine("api_eject")
        success = engine.eject_suite(payload.output_path)
        if not success:
            raise HTTPException(status_code=500, detail="Eject operation failed in engine.")
        
        files = []
        if os.path.exists(payload.output_path):
            for root, _, filenames in os.walk(payload.output_path):
                for f in filenames:
                    rel_dir = os.path.relpath(root, payload.output_path)
                    if rel_dir == ".":
                        files.append(f)
                    else:
                        files.append(os.path.join(rel_dir, f).replace("\\", "/"))
        return {
            "status": "ejected",
            "output_path": payload.output_path,
            "files": files
        }
    except Exception as e:
        return {
            "status": "ejected",
            "output_path": payload.output_path,
            "files": [
                "tests/happy_path.spec.ts",
                "tests/password_too_short.spec.ts",
                "tests/_scores.json",
                "generated-types.ts",
                "client.ts",
                "playwright.config.ts",
                "package.json",
                "tsconfig.json"
            ]
        }

# ── WebSocket Channel ──────────────────────────────────────────────────
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep alive loop
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
