"""
CHERENKOV web/api.py — FastAPI review backend, wired to the real HitlQueue.
"""

from __future__ import annotations

import os
import uuid
import asyncio
import sqlite3
import threading
import logging
from contextlib import asynccontextmanager


from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
    HTTPException,
    UploadFile,
    File,
    Form,
    Depends,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cherenkov.core.settings import get_settings
from cherenkov.stages.ingest import IngestStage
from cherenkov.core.orchestrator import OrchestrationEngine
from cherenkov.execution.validate import ValidationEngine
from cherenkov.hitl.store import HitlQueue

from cherenkov.web import divergences as divergence_store
from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry

import re as _re
import contextlib as _contextlib
from urllib.parse import urlparse as _urlparse
import ipaddress as _ipaddress
import socket as _socket


def _validate_scenario_id(scenario_id: str) -> str:
    if not _re.match(r"^[a-zA-Z0-9_\-]{1,128}$", scenario_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid scenario_id: must be alphanumeric/underscore/hyphen, max 128 chars",
        )
    return scenario_id


def _validate_output_path(path: str) -> str:
    resolved = os.path.realpath(os.path.abspath(path))
    allowed_base = os.path.realpath(os.path.abspath("."))
    # Use os.sep suffix to avoid prefix collision (e.g. /app vs /app_secret).
    if resolved != allowed_base and not resolved.startswith(allowed_base + os.sep):
        raise HTTPException(
            status_code=400, detail="Output path must be within the working directory"
        )
    return resolved


def _is_safe_ip(addr: "_ipaddress.IPv4Address | _ipaddress.IPv6Address") -> bool:
    return not (
        addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    )


async def _validate_spec_url(url: str) -> str:
    """Validate URL and return a TOCTOU-safe fetch URL.

    Resolves the hostname once, validates every returned IP, then rewrites the
    URL to use the first resolved IP so the subsequent requests.get call never
    triggers a second DNS lookup.  This closes the DNS-rebinding window between
    validation and fetch.
    """
    parsed = _urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")
    host = parsed.hostname or ""
    if host.lower() in (
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
    ):
        raise HTTPException(status_code=400, detail="Internal network URLs not allowed")
    try:
        # Literal IP in the URL — validate in-place, no rewrite needed.
        addr = _ipaddress.ip_address(host)
        if not _is_safe_ip(addr):
            raise HTTPException(
                status_code=400, detail="Internal network URLs not allowed"
            )
        return url
    except ValueError:
        pass
    # Hostname: resolve once, validate all IPs, return URL rewritten to the
    # first safe IP so requests.get never does a second DNS lookup.
    try:
        infos = await asyncio.to_thread(_socket.getaddrinfo, host, None)
    except _socket.gaierror:
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    if not infos:
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    first_ip: str | None = None
    for info in infos:
        addr_str = info[4][0]
        try:
            resolved_addr = _ipaddress.ip_address(addr_str)
            if not _is_safe_ip(resolved_addr):
                raise HTTPException(
                    status_code=400, detail="Internal network URLs not allowed"
                )
            if first_ip is None:
                first_ip = addr_str
        except ValueError:
            pass
    if first_ip is None:
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    # Rewrite to pre-resolved IP; requests must send Host header for SNI/vhosts.
    safe_url = parsed._replace(netloc=parsed.netloc.replace(host, first_ip, 1)).geturl()
    return safe_url


main_loop = None


@asynccontextmanager
async def lifespan(app_: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    yield


app = FastAPI(
    title="CHERENKOV QA Observability Dashboard Server",
    version="1.3.0",
    description="Localhost-first dashboard server for API conformance testing.",
    lifespan=lifespan,
)

# ── Phase 1: Knowledge Mesh API ─────────────────────────────────────────────────
from cherenkov.knowledge.api.routes import router as knowledge_router  # noqa: E402

app.include_router(knowledge_router)

# ── Phase 4: Chat Agent API ────────────────────────────────────────────────────
from cherenkov.chat.api.routes import router as chat_router  # noqa: E402

app.include_router(chat_router)

# ── Sprint 1: SDD Agent Cockpit API ─────────────────────────────────────────
from cherenkov.web.sdd_routes import router as sdd_router  # noqa: E402

app.include_router(sdd_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Phase 0b: Monitoring & Security (conditionally added) ────────────
from cherenkov.web.monitoring import router as monitor_router  # noqa: E402

app.include_router(monitor_router)

from cherenkov.web.routes.metrics_routes import router as metrics_router  # noqa: E402

app.include_router(metrics_router)

from cherenkov.web.routes.conformance_routes import router as conformance_router  # noqa: E402

app.include_router(conformance_router)

from cherenkov.web.routes.static_routes import router as static_router  # noqa: E402

app.include_router(static_router)

from cherenkov.web.routes.data_routes import router as data_router  # noqa: E402

app.include_router(data_router)

from cherenkov.web.middleware.security import add_security_middleware  # noqa: E402

add_security_middleware(app)

# ── Issue #196: HITL Auth — API key authentication ──────────────────────
# Only active when CHERENKOV_HITL_API_KEY is set (single-user by default).
# Clients provide the key via X-API-Key header or Authorization: Bearer <key>.


async def verify_api_key(
    x_api_key: str | None = Header(None), authorization: str | None = Header(None)
):
    import hmac as _hmac

    configured_key = get_settings().HITL_API_KEY
    if not configured_key:
        return  # no auth configured — allow all
    if x_api_key and _hmac.compare_digest(x_api_key, configured_key):
        return
    if (
        authorization
        and authorization.startswith("Bearer ")
        and _hmac.compare_digest(authorization[7:], configured_key)
    ):
        return
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key. Set CHERENKOV_HITL_API_KEY env var.",
    )


# ── WebSocket Manager ──────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, message: dict):
        async with self._lock:
            conns = list(self.active_connections)
        dead = []
        for connection in conns:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        if dead:
            async with self._lock:
                for c in dead:
                    try:
                        self.active_connections.remove(c)
                    except ValueError:
                        pass


manager = ConnectionManager()


def ws_event_callback(type_: str, payload: dict):
    if main_loop and manager.active_connections:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": type_, "payload": payload}), main_loop
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
# Sidecar health — used by Tauri desktop host to detect engine readiness
#
@app.get("/healthz")
async def healthz():
    return {"ok": True, "version": "1.0.0"}


#
# Token consumption monitor
#
@app.get("/api/v1/tokens/report")
async def tokens_report(days: int = 30):
    """Token consumption report: usage by provider/stage, daily trend, recommendations."""
    from cherenkov.observability.token_monitor import get_monitor

    monitor = get_monitor()
    return monitor.get_dashboard_data(days=days)


@app.get("/api/v1/tokens/recommendations")
async def tokens_recommendations(days: int = 30):
    """Return only the actionable cost-reduction recommendations."""
    from cherenkov.observability.token_monitor import get_monitor

    monitor = get_monitor()
    report = monitor.get_report(days=days)
    return {
        "recommendations": report.recommendations,
        "total_cost_usd": report.total_cost_usd,
        "period_days": days,
    }


#
# Health
#
@app.get("/api/v1/health")
async def health_check():
    try:
        device = await asyncio.wait_for(
            asyncio.to_thread(get_settings().detect_ollama_device), timeout=2.0
        )
    except Exception:
        device = "unknown"
    return {
        "status": "online",
        "device": device,
        "gen_model": get_settings().GEN_MODEL,
        "active_connections": len(manager.active_connections),
        "workspace_root": os.getcwd(),
        "demo_mode": os.environ.get("DEMO_MODE") == "1",
    }


#
# Doctor
#
@app.get("/api/v1/doctor")
async def run_doctor_api():
    from cherenkov.stages.doctor_cmd import (
        check_ollama_binary,
        check_ollama_daemon,
        check_node,
        check_npx_playwright,
        check_prism_docker,
        check_egress_blocked,
    )
    from cherenkov.core.config_loader import load_effective_config
    from cherenkov.core.settings import get_settings

    cfg = load_effective_config()
    checks = []

    ollama_bin, bin_det = check_ollama_binary()
    checks.append(
        {
            "name": "Ollama Binary",
            "status": "passed" if ollama_bin else "failed",
            "message": bin_det,
        }
    )

    if ollama_bin:
        ollama_daemon, daemon_det = check_ollama_daemon()
        checks.append(
            {
                "name": "Ollama Daemon",
                "status": "passed" if ollama_daemon else "failed",
                "message": daemon_det,
            }
        )

    node_ok, node_det = check_node()
    checks.append(
        {
            "name": "Node.js",
            "status": "passed" if node_ok else "failed",
            "message": node_det,
        }
    )

    pw_ok, pw_det = check_npx_playwright()
    checks.append(
        {
            "name": "Playwright",
            "status": "passed" if pw_ok else "failed",
            "message": pw_det,
        }
    )

    prism_ok, prism_det = check_prism_docker()
    checks.append(
        {
            "name": "Prism Docker",
            "status": "passed" if prism_ok else "failed",
            "message": prism_det,
        }
    )

    egress_ok, egress_det = check_egress_blocked(cfg)
    checks.append(
        {
            "name": "Egress Policy",
            "status": "passed" if egress_ok else "failed",
            "message": egress_det,
        }
    )

    device = get_settings().detect_ollama_device()
    is_gpu = device == "GPU"
    checks.append(
        {
            "name": "Device",
            "status": "passed" if is_gpu else "failed",
            "message": device + " (GPU recommended)",
        }
    )

    ready = ollama_bin and node_ok and pw_ok and prism_ok

    return {"checks": checks, "ready": ready}


#
# Ingest
#
@app.post("/api/v1/ingest")
async def ingest_spec_file(
    file: UploadFile | None = File(None), url: str | None = Form(None)
):
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
            MAX_SPEC_BYTES = 10 * 1024 * 1024  # 10 MB
            content = await file.read(MAX_SPEC_BYTES + 1)
            if len(content) > MAX_SPEC_BYTES:
                raise HTTPException(
                    status_code=413, detail="Spec file exceeds 10MB limit"
                )
            with open(spec_path, "wb") as f:
                f.write(content)
        elif url:
            import requests

            original_host = _urlparse(url).hostname or ""
            safe_url = await _validate_spec_url(url)
            # Pass original Host header so SNI / virtual-hosting works when
            # the URL was rewritten to a pre-resolved IP.
            resp = await asyncio.to_thread(
                requests.get, safe_url, timeout=15,
                headers={"Host": original_host} if safe_url != url else {},
            )
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
            "richness": sum(ep["richness"] for ep in endpoints) / len(endpoints)
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
async def trigger_pipeline_run(
    payload: RunPipelinePayload,
    background_tasks: BackgroundTasks,
    _auth=Depends(verify_api_key),
):
    from cherenkov.stages.doctor_cmd import run_doctor

    # 1. Doctor Preflight Check — suppress stdout to avoid polluting API response body
    import io

    with _contextlib.redirect_stdout(io.StringIO()):
        doctor_status = run_doctor()

    # If demo mode is on, bypass doctor and just inject mock findings
    if payload.demo_mode:
        from cherenkov.execution.demo_mode import generate_demo_findings

        generate_demo_findings()
        return {"run_id": "demo", "status": "demo_completed"}

    # Warn but do not necessarily block if there are minor issues (e.g., CPU mode)
    if doctor_status != 0:
        print(
            "Warning: Doctor preflight checks reported issues (could be missing GPU or daemon state). Continuing anyway."
        )

    run_id = str(uuid.uuid4())[:8]
    if not os.path.exists(payload.spec_path):
        raise HTTPException(
            status_code=404, detail="Ingested spec file path not found."
        )
    thread = threading.Thread(
        target=run_pipeline_thread, args=(payload.spec_path, run_id)
    )
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

    def _scan() -> list[dict]:
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


#
# Review — wired to real HitlQueue (Issue 173)
#
@app.get("/api/v1/review/queue")
async def list_review_queue(
    status: str | None = "pending", _auth=Depends(verify_api_key)
):
    """List HITL queue items from the live SQLite queue."""
    queue = get_queue()
    items = queue.list(status=status)
    tests_dir = os.path.abspath(os.path.join(os.getcwd(), "stub/generated_tests"))

    def _load_all_codes() -> dict[str, str | None]:
        codes: dict[str, str | None] = {}
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


@app.post("/api/v1/review/approve")
async def approve_review_item(
    payload: ReviewActionPayload, _auth=Depends(verify_api_key)
):
    """Approve a pending HITL item via HitlQueue and feed positive verdict to Reflector."""
    queue = get_queue()
    actor = os.environ.get("USER", "dashboard")
    envelope = queue.approve(payload.scenario_id, actor=actor, source="web")
    if not envelope.ok:
        raise HTTPException(
            status_code=409
            if envelope.error and envelope.error.code == "conflict"
            else 404,
            detail=envelope.error.message if envelope.error else "approve failed",
        )

    store = FeedbackStore()
    store.record_feedback(
        FeedbackEntry(
            hitl_item_id=payload.scenario_id,
            action="approve",
            reason=payload.reason or "Approved by reviewer",
        )
    )

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
        logging.getLogger("HITL").warning(
            "failed to feed approve verdict to Reflector", exc_info=e
        )

    return {"status": "approved", "scenario_id": payload.scenario_id}


@app.post("/api/v1/review/reject")
async def reject_review_item(
    payload: ReviewActionPayload, _auth=Depends(verify_api_key)
):
    """Reject a pending HITL item via HitlQueue and feed negative verdict to Reflector."""
    queue = get_queue()
    actor = os.environ.get("USER", "dashboard")
    reason = payload.reason or "Rejected by reviewer"
    envelope = queue.reject(
        payload.scenario_id, actor=actor, reason=reason, source="web"
    )
    if not envelope.ok:
        raise HTTPException(
            status_code=409
            if envelope.error and envelope.error.code == "conflict"
            else 404,
            detail=envelope.error.message if envelope.error else "reject failed",
        )

    store = FeedbackStore()
    store.record_feedback(
        FeedbackEntry(hitl_item_id=payload.scenario_id, action="reject", reason=reason)
    )

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
        logging.getLogger("HITL").warning(
            "failed to feed reject verdict to Reflector", exc_info=e
        )

    return {"status": "rejected", "scenario_id": payload.scenario_id}


@app.post("/api/v1/review/edit")
async def edit_review_item(payload: ReviewActionPayload, _auth=Depends(verify_api_key)):
    """Save edited test code (filesystem, not in queue)."""
    if not payload.test_code:
        raise HTTPException(
            status_code=400, detail="Missing updated test code content."
        )
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


@app.post("/api/v1/review/classify")
async def classify_review_item(payload: ClassifyPayload, _auth=Depends(verify_api_key)):
    """Classify a HITL item as regression, intended, or ignore."""
    queue = get_queue()
    actor = payload.actor or os.environ.get("USER", "dashboard")
    if payload.classification == "regression":
        envelope = queue.approve(payload.item_id, actor=actor, source="web")
    elif payload.classification == "intended":
        envelope = queue.reject(
            payload.item_id,
            actor=actor,
            reason=payload.detail or "classified as intended",
            source="web",
        )
    elif payload.classification == "ignore":
        envelope = queue.ignore(payload.item_id, actor, source="web")
    else:
        raise HTTPException(
            status_code=400, detail=f"Unknown classification: {payload.classification}"
        )
    if not envelope.ok:
        raise HTTPException(
            status_code=409
            if envelope.error and envelope.error.code == "conflict"
            else 404,
            detail=envelope.error.message if envelope.error else "classify failed",
        )
    return {
        "status": "classified",
        "item_id": payload.item_id,
        "classification": payload.classification,
    }


#
# Validate
#
@app.post("/api/v1/validate")
async def validate_test_suite(payload: ValidatePayload, _auth=Depends(verify_api_key)):
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


#
# Eject
#
@app.post("/api/v1/eject")
async def eject_test_suite(payload: EjectPayload, _auth=Depends(verify_api_key)):
    try:
        safe_path = _validate_output_path(payload.output_path)
        from cherenkov.execution.eject import EjectorEngine

        engine = EjectorEngine("api_eject")
        success = engine.eject_suite(safe_path)
        if not success:
            raise HTTPException(
                status_code=500, detail="Eject operation failed in engine."
            )
        files = []
        if os.path.exists(safe_path):
            for root, _, filenames in os.walk(safe_path):
                for f in filenames:
                    rel_dir = os.path.relpath(root, safe_path)
                    if rel_dir == ".":
                        files.append(f)
                    else:
                        files.append(os.path.join(rel_dir, f).replace("\\", "/"))
        return {"status": "ejected", "output_path": safe_path, "files": files}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eject operation failed: {e}")


#
# Divergences
#
@app.get("/api/v1/divergences")
async def list_divergences():
    return divergence_store.list_divergences()


@app.post("/api/v1/divergences/act")
async def act_on_divergence(payload: DivergenceActionPayload, _auth=Depends(verify_api_key)):
    try:
        new_status = divergence_store.apply_action(
            payload.divergence_id, payload.action
        )
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Unknown divergence id: {payload.divergence_id}"
        )
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")
    return {
        "status": "ok",
        "divergence_id": payload.divergence_id,
        "action": payload.action,
        "new_status": new_status,
    }


#
# Mobile Pilot
#
_mobile_pilot_status = {
    "status": "idle",
    "current_step": 0,
    "total_steps": 6,
    "steps": [
        {
            "step_id": "1",
            "action": "Connect device",
            "target": "android-emulator",
            "expected": "device online",
            "actual": "",
            "status": "pending",
        },
        {
            "step_id": "2",
            "action": "Install APK",
            "target": "app-debug.apk",
            "expected": "install success",
            "actual": "",
            "status": "pending",
        },
        {
            "step_id": "3",
            "action": "Launch app",
            "target": "com.example.app",
            "expected": "app foreground",
            "actual": "",
            "status": "pending",
        },
        {
            "step_id": "4",
            "action": "Run login test",
            "target": "LoginScreen",
            "expected": "200 OK",
            "actual": "",
            "status": "pending",
        },
        {
            "step_id": "5",
            "action": "Run checkout flow",
            "target": "CheckoutScreen",
            "expected": "order confirmed",
            "actual": "",
            "status": "pending",
        },
        {
            "step_id": "6",
            "action": "Collect logs",
            "target": "logcat",
            "expected": "logs saved",
            "actual": "",
            "status": "pending",
        },
    ],
}


@app.get("/api/v1/mobile/pilot/status")
async def get_mobile_pilot_status():
    return _mobile_pilot_status


@app.post("/api/v1/mobile/pilot/start")
async def start_mobile_pilot():
    _mobile_pilot_status["status"] = "running"
    return {"status": "started"}


# ── Projects ─────────────────────────────────────────────────────────────────


@app.get("/api/v1/projects")
async def get_projects():
    """Return a list of projects derived from the workspace layout."""
    workspace = os.getcwd()
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()

    def _query_projects() -> dict:
        conn = sqlite3.connect(store.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN outcome='approve' THEN 1 ELSE 0 END) as approved "
                "FROM verdicts"
            )
            row = cursor.fetchone()
            return dict(row) if row else {}
        except Exception:
            return {}
        finally:
            conn.close()

    try:
        row_data = await asyncio.to_thread(_query_projects)
        total = row_data.get("total") or 0
        approved = row_data.get("approved") or 0
        pass_rate = round((approved / total) * 100) if total > 0 else 0
    except Exception:
        total, pass_rate = 0, 0

    return [
        {
            "id": "default",
            "name": os.path.basename(workspace) or "cherenkov",
            "lastRun": "",
            "pipelineStatus": {
                "ingest": "queued",
                "plan": "queued",
                "generate": "queued",
                "review": "queued",
            },
            "stats": {"testsCount": total, "passRate": pass_rate, "healingCount": 0},
            "sparkline": [],
        }
    ]


# ── Settings ──────────────────────────────────────────────────────────────────

_settings: dict = {
    "target": {"url": "http://localhost:8000", "auth_header": ""},
    "engine": {
        "model_tier": "local",
        "enable_demo_mode": False,
        "execution_budget": 100,
        "workers": 4,
    },
    "security": {"egress_policy": "strict", "auth_secret": ""},
    "ui": {"density": "comfortable", "reduced_motion": False},
}


@app.get("/api/v1/settings")
async def api_get_settings(_auth=Depends(verify_api_key)):
    redacted = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _settings.items()}
    if "auth_secret" in redacted.get("security", {}):
        redacted["security"]["auth_secret"] = "***" if redacted["security"]["auth_secret"] else ""
    return redacted


_SETTINGS_PROTECTED_FIELDS = {"security": {"auth_secret", "egress_policy"}}


@app.put("/api/v1/settings")
async def update_settings(body: dict, _auth=Depends(verify_api_key)):
    for key, val in body.items():
        if key in _settings and isinstance(val, dict):
            protected = _SETTINGS_PROTECTED_FIELDS.get(key, set())
            for sub_key, sub_val in val.items():
                if sub_key in protected:
                    continue
                _settings[key][sub_key] = sub_val
        elif key in _settings and key not in _SETTINGS_PROTECTED_FIELDS:
            _settings[key] = val
    return _settings


# ── Governance ────────────────────────────────────────────────────────────────


@app.get("/api/v1/governance")
async def get_governance():
    """Return governance health score, policy issues, model certification, and traceability."""
    from cherenkov.ai.accounting import CostAccountant

    accountant = CostAccountant()
    kpi = accountant.get_governance_kpis()
    fp_rate = kpi.get("false_positive_rate", 0.0)
    score = max(0, round(100 - fp_rate * 100))
    issues = []
    if fp_rate > 0.05:
        issues.append(
            {
                "id": "high-fp",
                "severity": "high",
                "message": f"False positive rate {fp_rate:.1%} exceeds 5% threshold",
            }
        )
    return {
        "score": score,
        "issues": issues,
        "defectEscapeRate": kpi.get("defect_escape_rate", 0.0),
        "falsePositiveRate": fp_rate,
        "modelCertification": [
            {
                "model": "claude-3-5-sonnet",
                "status": "certified",
                "tier": "expert",
                "reason": "Automated clearance via CI/CD",
            },
            {
                "model": "llama-3-8b",
                "status": "pending",
                "tier": "fast",
                "reason": "Awaiting human review",
            },
        ],
        "traceability": [
            {
                "action": "Validation",
                "target": "/api/pets",
                "user": "AI Pilot",
                "timestamp": "2026-06-12T10:00:00Z",
            }
        ],
    }


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
        await manager.disconnect(websocket)


#
