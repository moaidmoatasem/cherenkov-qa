"""
cherenkov/web/routes/system.py — System/health/settings routes.
"""

from __future__ import annotations

import os
import asyncio
import sqlite3

from fastapi import APIRouter, Depends

from cherenkov.core.settings import get_settings
from cherenkov.web.deps import verify_api_key, manager

router = APIRouter()


#
# Sidecar health — used by Tauri desktop host to detect engine readiness
#
@router.get("/healthz")
async def healthz():
    return {"ok": True, "version": "1.0.0"}


#
# Health
#
@router.get("/api/v1/health")
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
@router.get("/api/v1/doctor")
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
# Token consumption monitor
#
@router.get("/api/v1/tokens/report")
async def tokens_report(days: int = 30):
    """Token consumption report: usage by provider/stage, daily trend, recommendations."""
    from cherenkov.observability.token_monitor import get_monitor

    monitor = get_monitor()
    return monitor.get_dashboard_data(days=days)


@router.get("/api/v1/tokens/recommendations")
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


# ── Projects ──────────────────────────────────────────────────────────────────


@router.get("/api/v1/projects")
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


# ── Settings ───────────────────────────────────────────────────────────────────

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


@router.get("/api/v1/settings")
async def api_get_settings(_auth=Depends(verify_api_key)):
    redacted = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _settings.items()}
    if "auth_secret" in redacted.get("security", {}):
        redacted["security"]["auth_secret"] = "***" if redacted["security"]["auth_secret"] else ""
    return redacted


_SETTINGS_PROTECTED_FIELDS = {"security": {"auth_secret", "egress_policy"}}


@router.put("/api/v1/settings")
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
