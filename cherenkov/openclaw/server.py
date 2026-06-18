from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.hitl.contracts import HitlEnvelope
from cherenkov.openclaw.adapter import OpenClawAdapter
from cherenkov.openclaw.contracts import (
    OpenClawConfig,
    TriggerRequest,
    ClassificationRequest,
)
from cherenkov.adapters.notifiers.slack import SlackNotifier
from cherenkov.adapters.notifiers.webhook import WebhookNotifier

_HAS_FASTAPI = False
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    _HAS_FASTAPI = True
except ImportError:
    FastAPI = None  # type: ignore


def create_app(
    adapter: OpenClawAdapter | None = None,
    config: OpenClawConfig | None = None,
) -> Any:
    """Create a FastAPI app wrapping the OpenClaw adapter.

    When FastAPI is not available, raises RuntimeError.
    """
    if not _HAS_FASTAPI:
        raise RuntimeError(
            "FastAPI is required for the OpenClaw HTTP server. "
            "Install it with: pip install fastapi uvicorn"
        )

    app = FastAPI(title="OpenClaw Tier-1 Adapter", version="1.0.0")
    cfg = config or OpenClawConfig()
    adp = adapter or OpenClawAdapter(config=cfg)

    # Wire up notifiers
    slack_notifier = SlackNotifier()
    adp.on_notify(slack_notifier.notify)  # type: ignore

    webhook_notifier = WebhookNotifier(webhook_url=cfg.notification_endpoint)
    adp.on_notify(webhook_notifier.notify)

    def _to_json_response(env: HitlEnvelope, status_code: int = 200) -> JSONResponse:
        data = env.model_dump()
        if env.ok:
            return JSONResponse(content=data, status_code=status_code)
        http_status = (
            409
            if env.error and env.error.code == "conflict"
            else 404
            if env.error and env.error.code == "not_found"
            else 400
        )
        return JSONResponse(content=data, status_code=http_status)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "openclaw-tier1"}

    @app.get("/hitl/list")
    async def hitl_list(status: str | None = "pending"):
        return _to_json_response(adp.list_envelope(status=status))

    @app.get("/hitl/show/{item_id}")
    async def hitl_show(item_id: str):
        return _to_json_response(adp.show_envelope(item_id))

    @app.post("/hitl/approve/{item_id}")
    async def hitl_approve(item_id: str, request: Request):
        body = (
            await request.json()
            if request.headers.get("content-type") == "application/json"
            else {}
        )
        actor = body.get("actor", os.environ.get("USER", "openclaw"))
        chat_user_id = body.get("chat_user_id")
        return _to_json_response(
            adp.approve_envelope(item_id, actor, chat_user_id=chat_user_id)
        )

    @app.post("/hitl/reject/{item_id}")
    async def hitl_reject(item_id: str, request: Request):
        body = (
            await request.json()
            if request.headers.get("content-type") == "application/json"
            else {}
        )
        actor = body.get("actor", os.environ.get("USER", "openclaw"))
        reason = body.get("reason", "rejected via openclaw")
        chat_user_id = body.get("chat_user_id")
        return _to_json_response(
            adp.reject_envelope(item_id, actor, reason, chat_user_id=chat_user_id)
        )

    @app.post("/hitl/lock/{item_id}")
    async def hitl_lock(item_id: str, request: Request):
        body = await request.json()
        chat_user_id = body.get("chat_user_id", "")
        return _to_json_response(adp.lock_envelope(item_id, chat_user_id))

    @app.post("/hitl/classify/{item_id}")
    async def hitl_classify(item_id: str, request: Request):
        body = await request.json()
        req = ClassificationRequest(
            item_id=item_id,
            classification=body.get("classification", "intended"),
            actor=body.get("actor", os.environ.get("USER", "openclaw")),
            detail=body.get("detail", ""),
        )
        return _to_json_response(adp.classify_envelope(req))

    @app.post("/hitl/trigger")
    async def hitl_trigger(request: Request):
        body = await request.json()
        trigger = TriggerRequest(**body)
        return _to_json_response(adp.trigger_run(trigger))

    @app.get("/hitl/poll")
    async def hitl_poll():
        return _to_json_response(adp.poll_envelope())

    @app.get("/hitl/explain/{item_id}")
    @app.post("/hitl/explain/{item_id}")
    async def hitl_explain(item_id: str):
        return _to_json_response(adp.explain_envelope(item_id))

    return app


def serve(config: OpenClawConfig | None = None) -> None:
    """Run the OpenClaw HTTP server (blocking)."""
    if not _HAS_FASTAPI:
        print(
            "ERROR: FastAPI + uvicorn required. pip install fastapi uvicorn",
            file=sys.stderr,
        )
        sys.exit(1)

    import uvicorn

    cfg = config or OpenClawConfig()
    app = create_app(config=cfg)
    log = get_logger("OPENCLAW")
    log.info("starting openclaw tier-1 server", host=cfg.host, port=cfg.port)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


def serve_background(
    adapter: OpenClawAdapter | None = None,
    config: OpenClawConfig | None = None,
) -> tuple[Any, threading.Thread]:
    """Start the OpenClaw server in a background thread.

    Returns (app, thread) for use in tests.
    """
    if not _HAS_FASTAPI:
        raise RuntimeError("FastAPI is required for the OpenClaw HTTP server.")

    import uvicorn
    from threading import Thread

    cfg = config or OpenClawConfig()
    app = create_app(adapter=adapter, config=cfg)

    class ServerThread(Thread):
        def __init__(self):
            super().__init__(daemon=True)
            self._config = uvicorn.Config(
                app, host=cfg.host, port=cfg.port, log_level="warning"
            )
            self._server = uvicorn.Server(self._config)

        def run(self):
            self._server.run()

        def stop(self):
            self._server.should_exit = True

    thread = ServerThread()
    thread.start()
    time.sleep(0.5)  # wait for server to start
    return app, thread
