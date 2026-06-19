"""
CHERENKOV web/api.py — FastAPI review backend, wired to the real HitlQueue.
"""

from __future__ import annotations


from fastapi import (
    FastAPI,
)
from fastapi.middleware.cors import CORSMiddleware



from cherenkov.web.routes.deps import (
    lifespan,
)



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

from cherenkov.web.routes.health_routes import router as health_router  # noqa: E402

app.include_router(health_router)

from cherenkov.web.routes.divergence_routes import router as divergence_router  # noqa: E402

app.include_router(divergence_router)

from cherenkov.web.routes.mobile_routes import router as mobile_router  # noqa: E402

app.include_router(mobile_router)

from cherenkov.web.routes.workspace_routes import router as workspace_router  # noqa: E402

app.include_router(workspace_router)

from cherenkov.web.routes.review_routes import router as review_router  # noqa: E402

app.include_router(review_router)

from cherenkov.web.routes.ops_routes import router as ops_router  # noqa: E402

app.include_router(ops_router)

from cherenkov.web.middleware.security import add_security_middleware  # noqa: E402

add_security_middleware(app)
