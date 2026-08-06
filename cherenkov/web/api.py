"""
CHERENKOV web/api.py — FastAPI review backend, wired to the real HitlQueue.
"""

from __future__ import annotations

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from cherenkov.web.routes.deps import (
    lifespan,
    manager,
)

app = FastAPI(
    title="CHERENKOV QA Observability Dashboard Server",
    version="1.3.0",
    description="Localhost-first dashboard server for API conformance testing.",
    lifespan=lifespan,
)


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """Live pipeline event stream. The broadcaster (ConnectionManager in
    deps.py) and every emitter (orchestrator._emit_event via
    ops_routes.ws_event_callback) already existed; this endpoint was the
    missing piece connecting client sockets to that broadcaster."""
    await manager.connect(websocket)
    try:
        while True:
            # The client doesn't send anything meaningful on this channel;
            # this just keeps the connection open until it disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

# ── Phase 1: Knowledge Mesh API ─────────────────────────────────────────────────
from cherenkov.knowledge.api.routes import router as knowledge_router

app.include_router(knowledge_router)

# ── Phase 4: Chat Agent API ────────────────────────────────────────────────────
from cherenkov.chat.api.routes import router as chat_router

app.include_router(chat_router)

# ── Sprint 1: SDD Agent Cockpit API ─────────────────────────────────────────
from cherenkov.web.sdd_routes import router as sdd_router

app.include_router(sdd_router)

from cherenkov.web.middleware.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware)

from cherenkov.web.middleware.auth_middleware import JWTAuthMiddleware

app.add_middleware(JWTAuthMiddleware)

from cherenkov.web.middleware.security import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)

# CORS is registered LAST so it is OUTERMOST — Starlette prepends each
# `add_middleware`, so the final call wraps everything before it. Registered
# first (as it was until 2026-07-31) it sat innermost, so any response produced
# *above* it carried no CORS headers: a 429 from the rate limiter, or a 401
# from JWT auth, reached the browser as an opaque CORS failure instead of the
# real status. Rate limiting was effectively invisible to the React UI.
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
from cherenkov.web.monitoring import router as monitor_router

app.include_router(monitor_router)

from cherenkov.web.routes.metrics_routes import router as metrics_router

app.include_router(metrics_router)

from cherenkov.web.routes.conformance_routes import router as conformance_router

app.include_router(conformance_router)

from cherenkov.web.routes.coverage_routes import router as coverage_router

app.include_router(coverage_router)

from cherenkov.web.routes.perf_routes import router as perf_router

app.include_router(perf_router)

from cherenkov.web.routes.data_routes import router as data_router

app.include_router(data_router)

from cherenkov.web.routes.health_routes import router as health_router

app.include_router(health_router)

from cherenkov.web.routes.divergence_routes import router as divergence_router

app.include_router(divergence_router)

from cherenkov.web.routes.certificate_routes import router as certificate_router

app.include_router(certificate_router)

from cherenkov.web.routes.mobile_routes import router as mobile_router

app.include_router(mobile_router)

from cherenkov.web.routes.workspace_routes import router as workspace_router

app.include_router(workspace_router)

from cherenkov.web.routes.review_routes import router as review_router

app.include_router(review_router)

from cherenkov.web.routes.ocr_routes import router as ocr_router

app.include_router(ocr_router)
from cherenkov.web.routes.teleport import router as teleport_router

app.include_router(teleport_router)

from cherenkov.web.routes.push_notify import router as push_notify_router

app.include_router(push_notify_router)
from cherenkov.web.routes.ops_routes import router as ops_router

app.include_router(ops_router)

from cherenkov.web.routes.agents import router as agents_router

app.include_router(agents_router)

from cherenkov.web.middleware.security import add_security_middleware

add_security_middleware(app)

from cherenkov.web.errors import install_error_handlers

install_error_handlers(app)

from cherenkov.web.auth.routes import router as auth_router

app.include_router(auth_router)

from cherenkov.web.routes.webhooks_github import github_webhook_router

app.include_router(github_webhook_router)
from cherenkov.scheduling.api.routes import router as routines_router

app.include_router(routines_router)

from cherenkov.web.routes.runs_router import router as runs_router

app.include_router(runs_router)

# ── Integrity-as-a-Service API (Pillar 5 — INNOVATION_ROADMAP_V2) ────────────
from cherenkov.integrity.api import router as integrity_router

app.include_router(integrity_router)

# ── Phase 14: alert policies + auto-regenerate (registered before the SPA
# fallback so GET /api/v1/{alerts,regenerate} routes are matched first) ──────
from cherenkov.web.routes.alerts_routes import router as alerts_router

app.include_router(alerts_router)

from cherenkov.web.routes.regenerate_routes import router as regenerate_router

app.include_router(regenerate_router)

# ── Journeys: workflow definitions + live per-step run state. Registered
# before the SPA fallback so /api/v1/journeys/* is matched first ─────────────
from cherenkov.web.routes.journey_routes import router as journey_router

app.include_router(journey_router)

# ── Static/SPA Fallback Route ──────────────────────────────────────────────────
from cherenkov.web.routes.static_routes import router as static_router

app.include_router(static_router)

