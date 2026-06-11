"""
CHERENKOV web/api.py — FastAPI review backend, wired to the real HitlQueue.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import json
import uuid
import asyncio
import shutil
import threading
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cherenkov.core.config import Config
from cherenkov.stages.ingest import IngestStage
from cherenkov.core.orchestrator import OrchestrationEngine
from cherenkov.execution.validate import ValidationEngine
from cherenkov.hitl.store import HitlQueue
from cherenkov.hitl.contracts import HitlItem, HitlStatus, ok_envelope, err_envelope

from cherenkov.web import divergences as divergence_store
from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry

app = FastAPI(
    title="CHERENKOV QA Observability Dashboard Server",
    version="1.3.0",
    description="Localhost-first dashboard server for API conformance testing."
)

# ── Phase 1: Knowledge Mesh API ─────────────────────────────────────────────────
from cherenkov.knowledge.api.routes import router as knowledge_router
app.include_router(knowledge_router)

# ── Phase 4: Chat Agent API ────────────────────────────────────────────────────
from cherenkov.chat.api.routes import router as chat_router
app.include_router(chat_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Phase 0b: Monitoring & Security (conditionally added) ────────────
from cherenkov.web.monitoring import router as monitor_router
app.include_router(monitor_router)

from cherenkov.web.middleware.security import add_security_middleware
add_security_middleware(app)

# ── Issue #196: HITL Auth — API key authentication ──────────────────────
# Only active when CHERENKOV_HITL_API_KEY is set (single-user by default).
# Clients provide the key via X-API-Key header or Authorization: Bearer <key>.

async def verify_api_key(x_api_key: str | None = Header(None), authorization: str | None = Header(None)):
    configured_key = Config.HITL_API_KEY
    if not configured_key:
        return  # no auth configured — allow all
    if x_api_key and x_api_key == configured_key:
        return
    if authorization and authorization.startswith("Bearer ") and authorization[7:] == configured_key:
        return
    raise HTTPException(status_code=401, detail="Missing or invalid API key. Set CHERENKOV_HITL_API_KEY env var.")

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
                pass

manager = ConnectionManager()
main_loop = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

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
    demo_mode: bool = False
    intent: str | None = None

class ReviewActionPayload(BaseModel):
    scenario_id: str
    reason: str | None = None
    test_code: str | None = None

class ValidatePayload(BaseModel):
    target_url: str

class EjectPayload(BaseModel):
    output_path: str

class DivergenceActionPayload(BaseModel):
    divergence_id: str
    action: str
    reason: str | None = None

class ClassifyPayload(BaseModel):
    item_id: str
    classification: str
    detail: str | None = None
    actor: str | None = None

# Singleton HitlQueue — backed by .cherenkov/hitl.db (or $CHERENKOV_HITL_DB)
_queue: HitlQueue | None = None

def get_queue() -> HitlQueue:
    global _queue
    if _queue is None:
        _queue = HitlQueue(db_path=os.getenv("CHERENKOV_HITL_DB"))
    return _queue

# ── Endpoints ──────────────────────────────────────────────────────────

#
# Health
#
@app.get("/api/v1/health")
async def health_check():
    try:
        device = await asyncio.wait_for(
            asyncio.to_thread(Config.detect_ollama_device),
            timeout=5.0
        )
    except Exception:
        device = "unknown"
    return {
        "status": "online",
        "device": device,
        "gen_model": Config.GEN_MODEL,
        "active_connections": len(manager.active_connections),
        "workspace_root": os.getcwd(),
        "demo_mode": os.environ.get("DEMO_MODE") == "1"
    }

#
# Doctor
#
@app.get("/api/v1/doctor")
async def run_doctor_api():
    from cherenkov.stages.doctor_cmd import (
        check_ollama_binary, check_ollama_daemon, check_node, 
        check_npx_playwright, check_prism_docker, check_egress_blocked
    )
    from cherenkov.core.config_loader import load_effective_config
    from cherenkov.core.config import Config
    
    cfg = load_effective_config()
    checks = []
    
    ollama_bin, bin_det = check_ollama_binary()
    checks.append({"name": "Ollama Binary", "status": "passed" if ollama_bin else "failed", "message": bin_det})
    
    if ollama_bin:
        ollama_daemon, daemon_det = check_ollama_daemon()
        checks.append({"name": "Ollama Daemon", "status": "passed" if ollama_daemon else "failed", "message": daemon_det})
    
    node_ok, node_det = check_node()
    checks.append({"name": "Node.js", "status": "passed" if node_ok else "failed", "message": node_det})
    
    pw_ok, pw_det = check_npx_playwright()
    checks.append({"name": "Playwright", "status": "passed" if pw_ok else "failed", "message": pw_det})
    
    prism_ok, prism_det = check_prism_docker()
    checks.append({"name": "Prism Docker", "status": "passed" if prism_ok else "failed", "message": prism_det})
    
    egress_ok, egress_det = check_egress_blocked(cfg)
    checks.append({"name": "Egress Policy", "status": "passed" if egress_ok else "failed", "message": egress_det})
    
    device = Config.detect_ollama_device()
    is_gpu = device == "GPU"
    checks.append({"name": "Device", "status": "passed" if is_gpu else "failed", "message": device + " (GPU recommended)"})
    
    ready = ollama_bin and node_ok and pw_ok and prism_ok
    
    return {"checks": checks, "ready": ready}

#
# Ingest
#
@app.post("/api/v1/ingest")
async def ingest_spec_file(
    file: UploadFile | None = File(None),
    url: str | None = Form(None)
):
    run_id = str(uuid.uuid4())[:8]
    temp_dir = os.path.abspath(os.path.join(os.getcwd(), ".cherenkov/temp_ingest"))
    os.makedirs(temp_dir, exist_ok=True)
    spec_path = os.path.join(temp_dir, f"spec_{run_id}.json" if (file and file.filename and file.filename.endswith('.json')) else f"spec_{run_id}.yaml")

    if not file and not url:
        raise HTTPException(status_code=400, detail="Either file upload or URL must be provided.")

    try:
        if file:
            with open(spec_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        elif url:
            import requests
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ('http', 'https'):
                raise HTTPException(status_code=400, detail="Invalid URL scheme. Only HTTP and HTTPS are allowed.")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(resp.text)

        ingest_stage = IngestStage(run_id)
        ingest_output = ingest_stage.run(spec_path)

        endpoints = []
        for ep in ingest_output.endpoints:
            missing = []
            for m in (ep.mutations or []):
                if hasattr(m, 'instruction') and m.instruction:
                    missing.append(m.instruction)
            endpoints.append({
                "path": ep.path,
                "method": ep.method,
                "richness": ep.richness,
                "missing_elements": missing
            })

        return {
            "spec_path": spec_path,
            "endpoints": endpoints,
            "richness": sum(ep["richness"] for ep in endpoints) / len(endpoints) if endpoints else 0.0
        }
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(spec_path):
            os.remove(spec_path)
        err_msg = getattr(e, 'detail', str(e)) if hasattr(e, 'status_code') else str(e)
        raise HTTPException(status_code=500, detail=f"Parsing error: {err_msg}")

#
# Pipeline run
#
def run_pipeline_thread(spec_path: str, run_id: str):
    try:
        engine = OrchestrationEngine(run_id=run_id, event_callback=ws_event_callback)
        engine.run_pipeline(spec_path)
    except Exception as e:
        ws_event_callback("pipeline_error", {"detail": str(e)})

@app.post("/api/v1/run")
async def trigger_pipeline_run(payload: RunPipelinePayload, background_tasks: BackgroundTasks, _auth=Depends(verify_api_key)):
    from cherenkov.stages.doctor_cmd import run_doctor
    
    # 1. Doctor Preflight Check (Issue 179)
    # Redirect stdout to suppress terminal noise if needed, but for now just run it
    import io, sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        doctor_status = run_doctor()
    finally:
        sys.stdout = old_stdout
        
    # If demo mode is on, bypass doctor and just inject mock findings
    if payload.demo_mode:
        from cherenkov.execution.demo_mode import generate_demo_findings
        generate_demo_findings()
        return {"run_id": "demo", "status": "demo_completed"}
        
    # Warn but do not necessarily block if there are minor issues (e.g., CPU mode)
    if doctor_status != 0:
        print("Warning: Doctor preflight checks reported issues (could be missing GPU or daemon state). Continuing anyway.")
        
    run_id = str(uuid.uuid4())[:8]
    if not os.path.exists(payload.spec_path):
        raise HTTPException(status_code=404, detail="Ingested spec file path not found.")
    thread = threading.Thread(target=run_pipeline_thread, args=(payload.spec_path, run_id))
    thread.daemon = True
    thread.start()
    return {"run_id": run_id, "status": "launched"}

#
# Tests
#
@app.get("/api/v1/tests")
async def list_generated_tests():
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    if not os.path.exists(tests_dir):
        return []
    tests = []
    for f in os.listdir(tests_dir):
        if f.endswith(".spec.ts"):
            file_path = os.path.join(tests_dir, f)
            with open(file_path, "r", encoding="utf-8") as file:
                code = file.read()
            scenario_id = f.replace(".spec.ts", "")
            tests.append({
                "name": f,
                "scenario_id": scenario_id,
                "endpoint": scenario_id,
                "method": "POST" if "create" in scenario_id else "GET",
                "code": code
            })
    return tests

#
# Review — wired to real HitlQueue (Issue 173)
#
@app.get("/api/v1/review/queue")
async def list_review_queue(status: str | None = "pending", _auth=Depends(verify_api_key)):
    """List HITL queue items from the live SQLite queue."""
    queue = get_queue()
    items = queue.list(status=status)
    return [
        {
            "id": item.id,
            "endpoint": item.endpoint,
            "method": item.method,
            "confidence": item.confidence,
            "confidence_reason": item.confidence_reason,
            "review_gate_failed": item.review_gate_failed,
            "status": item.status.value,
            "generated_test": None,
            "created_at": item.created_at,
        }
        for item in items
    ]

@app.post("/api/v1/review/approve")
async def approve_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    """Approve a pending HITL item via HitlQueue and feed positive verdict to Reflector."""
    queue = get_queue()
    actor = os.environ.get("USER", "dashboard")
    envelope = queue.approve(payload.scenario_id, actor=actor, source="web")
    if not envelope.ok:
        detail = envelope.error.detail if envelope.error else {}
        raise HTTPException(
            status_code=409 if envelope.error and envelope.error.code == "conflict" else 404,
            detail=envelope.error.message if envelope.error else "approve failed",
        )

    store = FeedbackStore()
    store.record_feedback(FeedbackEntry(
        hitl_item_id=payload.scenario_id,
        action="approve",
        reason=payload.reason or "Approved by reviewer",
    ))

    # Feed positive human verdict to Reflector
    try:
        from cherenkov.reflector.reflector import Reflector
        from cherenkov.core.contracts import VerdictOutcome
        reflector = Reflector(run_id="web")
        reflector.ingest_human_verdict(
            hypothesis_id=payload.scenario_id,
            outcome=VerdictOutcome.ACCEPT,
            detail=payload.reason or "Approved via review dashboard",
        )
    except Exception as e:
        logging.getLogger("HITL").warning("failed to feed approve verdict to Reflector", exc_info=e)

    return {"status": "approved", "scenario_id": payload.scenario_id}

@app.post("/api/v1/review/reject")
async def reject_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    """Reject a pending HITL item via HitlQueue and feed negative verdict to Reflector."""
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
    store.record_feedback(FeedbackEntry(
        hitl_item_id=payload.scenario_id, 
        action="reject", 
        reason=reason
    ))

    # Feed negative human verdict to Reflector
    try:
        from cherenkov.reflector.reflector import Reflector
        from cherenkov.core.contracts import VerdictOutcome
        reflector = Reflector(run_id="web")
        reflector.ingest_human_verdict(
            hypothesis_id=payload.scenario_id,
            outcome=VerdictOutcome.REJECT,
            detail=reason,
        )
    except Exception as e:
        logging.getLogger("HITL").warning("failed to feed reject verdict to Reflector", exc_info=e)

    return {"status": "rejected", "scenario_id": payload.scenario_id}

@app.post("/api/v1/review/edit")
async def edit_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    """Save edited test code (filesystem, not in queue)."""
    if not payload.test_code:
        raise HTTPException(status_code=400, detail="Missing updated test code content.")
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))
    os.makedirs(tests_dir, exist_ok=True)
    file_path = os.path.join(tests_dir, f"{payload.scenario_id}.spec.ts")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(payload.test_code)
    return {"status": "saved", "scenario_id": payload.scenario_id}

@app.post("/api/v1/review/classify")
async def classify_review_item(payload: ClassifyPayload, _auth=Depends(verify_api_key)):
    """Classify a HITL item as regression, intended, or ignore."""
    queue = get_queue()
    actor = payload.actor or os.environ.get("USER", "dashboard")
    if payload.classification == "regression":
        envelope = queue.approve(payload.item_id, actor=actor, source="web")
    elif payload.classification == "intended":
        envelope = queue.reject(payload.item_id, actor=actor,
                                 reason=payload.detail or "classified as intended", source="web")
    elif payload.classification == "ignore":
        from cherenkov.hitl.contracts import HitlStatus
        envelope = queue._resolve("hitl.classify", payload.item_id, actor, "web",
                                   HitlStatus.IGNORED, "", ())
    else:
        raise HTTPException(status_code=400, detail=f"Unknown classification: {payload.classification}")
    if not envelope.ok:
        raise HTTPException(
            status_code=409 if envelope.error and envelope.error.code == "conflict" else 404,
            detail=envelope.error.message if envelope.error else "classify failed",
        )
    return {"status": "classified", "item_id": payload.item_id, "classification": payload.classification}

#
# Validate
#
@app.post("/api/v1/validate")
async def validate_test_suite(payload: ValidatePayload):
    try:
        engine = ValidationEngine("api_validate")
        results = engine.validate_suite(payload.target_url)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#
# Eject
#
@app.post("/api/v1/eject")
async def eject_test_suite(payload: EjectPayload):
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
        return {"status": "ejected", "output_path": payload.output_path, "files": files}
    except Exception as e:
        return {"status": "ejected", "output_path": payload.output_path, "files": []}

#
# Divergences
#
@app.get("/api/v1/divergences")
async def list_divergences():
    return divergence_store.list_divergences()

@app.post("/api/v1/divergences/act")
async def act_on_divergence(payload: DivergenceActionPayload):
    try:
        new_status = divergence_store.apply_action(payload.divergence_id, payload.action)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown divergence id: {payload.divergence_id}")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")
    return {
        "status": "ok",
        "divergence_id": payload.divergence_id,
        "action": payload.action,
        "new_status": new_status,
    }

#
# Dashboard data endpoints (backed by real stores)
#
@app.get("/api/v1/overview")
async def get_overview():
    """Return overview with false-positive rate and recent learnings."""
    from cherenkov.ai.accounting import CostAccountant
    from cherenkov.reflector.store import VerdictStore
    from cherenkov.core.feedback_store import FeedbackStore
    from cherenkov.core.contracts import VerdictOutcome

    accountant = CostAccountant()
    kpi = accountant.get_governance_kpis()
    feedback = FeedbackStore()
    recent = feedback.get_all()[-10:] if feedback.get_all() else []

    return {
        "falsePositiveRate": kpi["false_positive_rate"],
        "maintenanceEfficiency": kpi["maintenance_efficiency"],
        "defectEscapeCount": kpi["defect_escape_count"],
        "totalVerdicts": kpi["total_verdicts"],
        "recentLearnings": [
            {"id": f.id, "action": f.action, "reason": f.reason, "timestamp": getattr(f, "timestamp", "")}
            for f in recent
        ],
    }

@app.get("/api/v1/truth-map")
async def get_truth_map():
    """Return learned idiom patterns from the VerdictStore."""
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()
    try:
        idioms = store.list_idioms(limit=50)
    except Exception:
        idioms = []
    return [
        {
            "id": i.id,
            "pattern": i.pattern,
            "divergence_class": i.divergence_class.value if i.divergence_class else "unknown",
            "endpoint": i.endpoint,
            "confirm_count": i.confirm_count,
            "decay_score": i.decay_score,
        }
        for i in idioms
    ]

@app.get("/api/v1/failures")
async def get_failures():
    """Return recent failure verdicts from the VerdictStore."""
    from cherenkov.reflector.store import VerdictStore
    from cherenkov.core.contracts import VerdictOutcome

    store = VerdictStore()
    conn = sqlite3.connect(store.db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT id, endpoint, outcome, failure_class, detail, timestamp "
            "FROM verdicts WHERE outcome IN (?, ?) "
            "ORDER BY timestamp DESC LIMIT 50",
            (VerdictOutcome.REJECT.value, VerdictOutcome.ESCAPED_DEFECT.value)
        )
        rows = [dict(r) for r in cursor.fetchall()]
    except Exception:
        rows = []
    finally:
        conn.close()
    return rows

@app.get("/api/v1/metrics")
async def get_metrics():
    """Return aggregated cost and latency metrics."""
    from cherenkov.ai.accounting import CostAccountant

    accountant = CostAccountant()
    report = accountant.report
    kpi = accountant.get_governance_kpis()
    return {
        "status": "ok",
        "metrics": {
            "requestCount": report.request_count,
            "totalTokens": report.total_tokens,
            "totalCost": report.total_cost,
            "totalDurationMs": report.total_duration_ms,
            "defectEscapeCount": kpi["defect_escape_count"],
            "falsePositiveRate": kpi["false_positive_rate"],
            "maintenanceEfficiency": kpi["maintenance_efficiency"],
        },
    }

#
# Mobile Pilot
#
_mobile_pilot_status = {
    "status": "idle",
    "current_step": 0,
    "total_steps": 6,
    "steps": [
        {"step_id": "1", "action": "Connect device", "target": "android-emulator", "expected": "device online", "actual": "", "status": "pending"},
        {"step_id": "2", "action": "Install APK", "target": "app-debug.apk", "expected": "install success", "actual": "", "status": "pending"},
        {"step_id": "3", "action": "Launch app", "target": "com.example.app", "expected": "app foreground", "actual": "", "status": "pending"},
        {"step_id": "4", "action": "Run login test", "target": "LoginScreen", "expected": "200 OK", "actual": "", "status": "pending"},
        {"step_id": "5", "action": "Run checkout flow", "target": "CheckoutScreen", "expected": "order confirmed", "actual": "", "status": "pending"},
        {"step_id": "6", "action": "Collect logs", "target": "logcat", "expected": "logs saved", "actual": "", "status": "pending"},
    ],
}

@app.get("/api/v1/mobile/pilot/status")
async def get_mobile_pilot_status():
    return _mobile_pilot_status

@app.post("/api/v1/mobile/pilot/start")
async def start_mobile_pilot():
    _mobile_pilot_status["status"] = "running"
    return {"status": "started"}

#
# WebSocket
#
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

#
# Static file serving for prebuilt UI
#
_ui_dist = os.path.join(os.path.dirname(__file__), "ui", "dist")

@app.get("/")
async def serve_index():
    index = os.path.join(_ui_dist, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "UI not built. Run `npm run build` in cherenkov/web/ui/."}

@app.get("/assets/{path:path}")
async def serve_assets(path: str):
    asset = os.path.join(_ui_dist, "assets", path)
    if os.path.exists(asset):
        return FileResponse(asset)
    raise HTTPException(status_code=404, detail="Asset not found")
