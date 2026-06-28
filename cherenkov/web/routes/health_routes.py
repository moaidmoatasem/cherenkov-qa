from fastapi import APIRouter, Depends

from cherenkov.web.routes.deps import manager
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role

router = APIRouter(tags=["health"])


@router.get("/healthz", operation_id="healthz_simple")
async def healthz_simple():
    return {"ok": True, "version": "1.0.0"}


@router.get("/api/v1/tokens/report")
async def tokens_report(days: int = 30):
    from cherenkov.observability.token_monitor import get_monitor
    monitor = get_monitor()
    return monitor.get_dashboard_data(days=days)


@router.get("/api/v1/tokens/recommendations")
async def tokens_recommendations(days: int = 30):
    from cherenkov.observability.token_monitor import get_monitor
    monitor = get_monitor()
    report = monitor.get_report(days=days)
    return {
        "recommendations": report.recommendations,
        "total_cost_usd": report.total_cost_usd,
        "period_days": days,
    }


@router.get("/api/v1/health")
async def health_check():
    import asyncio
    import os

    from cherenkov.core.settings import get_settings
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


@router.get("/api/v1/doctor")
async def run_doctor_api(_role=Depends(require_role(Role.admin))):
    from cherenkov.core.config_loader import load_effective_config
    from cherenkov.core.settings import get_settings
    from cherenkov.stages.doctor_cmd import (
        check_egress_blocked,
        check_node,
        check_npx_playwright,
        check_ollama_binary,
        check_ollama_daemon,
        check_prism_docker,
    )

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

    device = get_settings().detect_ollama_device()
    is_gpu = device == "GPU"
    checks.append({"name": "Device", "status": "passed" if is_gpu else "failed", "message": device + " (GPU recommended)"})

    ready = ollama_bin and node_ok and pw_ok and prism_ok
    return {"checks": checks, "ready": ready}


@router.get("/api/v1/flags")
async def get_feature_flags():
    """Return all feature flag values (resolved with env var / file / default priority)."""
    from cherenkov.core.flags import all_flags
    return {"flags": all_flags()}
