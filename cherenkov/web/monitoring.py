from __future__ import annotations

import time
import logging
from typing import Any

from fastapi import APIRouter, Response

from cherenkov.core.error_handling import get_degradation
from cherenkov.core.config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz")
async def healthz():
    degradation = get_degradation()
    status_code = 200 if degradation.health.level.value in ("healthy", "degraded") else 503
    return Response(
        content=json_dumps({
            "status": "ok" if status_code == 200 else "unhealthy",
            "level": degradation.health.level.value,
            "checks": dict(degradation.health.checks),
            "timestamp": time.time(),
        }),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/metrics")
async def metrics():
    degradation = get_degradation()
    h = degradation.health
    lines = [
        "# HELP cherenkov_health_level Current degradation level (0=healthy,3=down)",
        "# TYPE cherenkov_health_level gauge",
        f'cherenkov_health_level{{level="{h.level.value}"}} {["healthy","degraded","critical","down"].index(h.level.value)}',
        "",
        "# HELP cherenkov_checks_total Total health checks",
        "# TYPE cherenkov_checks_total gauge",
        f"cherenkov_checks_total {len(h.checks)}",
        "",
        "# HELP cherenkov_checks_passed Passed health checks",
        "# TYPE cherenkov_checks_passed gauge",
        f"cherenkov_checks_passed {sum(1 for v in h.checks.values() if v)}",
    ]
    for check_name, ok in h.checks.items():
        lines.append(f'cherenkov_check{{name="{check_name}"}} {1 if ok else 0}')
    lines.append("")
    return Response(content="\n".join(lines), media_type="text/plain")


@router.get("/api/v1/health/detail")
async def health_detail():
    degradation = get_degradation()
    return degradation.health.to_dict()


def json_dumps(data: dict[str, Any]) -> str:
    import json
    return json.dumps(data)
