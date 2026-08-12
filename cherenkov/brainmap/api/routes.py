"""HTTP API for the brain map.

Reads are served from the published SQLite graph and never re-scan, so the
dashboard stays fast on a large repo. The one write endpoint — ``/sync`` —
runs the scan on a worker thread behind a lock, because two concurrent syncs
of the same project would race on the same rows to no benefit.

Export deliberately takes no destination: the vault path comes from the
project profile, so an HTTP caller cannot ask the server to write markdown
into an arbitrary directory.
"""

from __future__ import annotations

import asyncio
import threading
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from cherenkov.brainmap.adapters.json_export import graph_payload
from cherenkov.brainmap.adapters.obsidian_vault import ObsidianVaultExporter
from cherenkov.brainmap.use_cases.sync import BrainMapEngine, build_engine
from cherenkov.web.sdd_auth import verify_api_key

router = APIRouter(prefix="/api/v1/brainmap", tags=["brainmap"])

_sync_lock = threading.Lock()


@lru_cache(maxsize=4)
def _engine() -> BrainMapEngine:
    """Return the process-wide engine for the server's working directory."""
    return build_engine()


def _split(value: str | None) -> list[str] | None:
    """Split a comma-separated filter parameter into a list."""
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@router.get("/status")
async def get_status(_auth=Depends(verify_api_key)) -> dict[str, Any]:
    """Return map statistics and the profile that produced them.

    Returns:
        dict[str, Any]: Stats, profile summary and whether a map exists yet.
    """
    engine = _engine()
    map_ = await asyncio.to_thread(engine.graph)
    stats = map_.stats()
    return {
        "exists": bool(stats["nodes"]),
        "stats": stats,
        "profile": engine.profile.to_dict(),
    }


@router.get("/graph")
async def get_graph(
    limit: int = Query(400, ge=1, le=5000),
    kinds: str | None = None,
    layers: str | None = None,
    q: str = "",
    _auth=Depends(verify_api_key),
) -> dict[str, Any]:
    """Return a filtered, ranked, size-bounded slice of the graph.

    Args:
        limit (int): Maximum nodes to return.
        kinds (str | None): Comma-separated node kinds to keep.
        layers (str | None): Comma-separated layers to keep.
        q (str): Substring match on node title or summary.

    Returns:
        dict[str, Any]: Nodes, edges, stats and truncation counts.
    """
    engine = _engine()
    map_ = await asyncio.to_thread(engine.graph)
    return graph_payload(map_, limit=limit, kinds=_split(kinds), layers=_split(layers), query=q)


@router.get("/neighborhood")
async def get_neighborhood(
    node_id: str,
    depth: int = Query(1, ge=1, le=5),
    limit: int = Query(300, ge=1, le=2000),
    _auth=Depends(verify_api_key),
) -> dict[str, Any]:
    """Return the subgraph around one node.

    Args:
        node_id (str): Canonical ``kind:slug`` node id.
        depth (int): Hops to expand.
        limit (int): Maximum nodes to return.

    Returns:
        dict[str, Any]: The neighbourhood in the same shape as ``/graph``,
        plus the focus node's full record.

    Raises:
        HTTPException: 404 when the node is not in the map.
    """
    engine = _engine()
    sub = await asyncio.to_thread(engine.neighborhood, node_id, depth)
    if node_id not in sub.nodes:
        raise HTTPException(status_code=404, detail=f"Unknown node: {node_id}")
    payload = graph_payload(sub, limit=limit)
    payload["focus"] = sub.nodes[node_id].to_dict()
    payload["depth"] = depth
    return payload


@router.get("/findings")
async def get_findings(
    severity: str | None = None,
    code: str | None = None,
    limit: int = Query(200, ge=1, le=2000),
    _auth=Depends(verify_api_key),
) -> dict[str, Any]:
    """Return reconciliation findings, worst first.

    Args:
        severity (str | None): Keep only this severity.
        code (str | None): Keep only this finding code.
        limit (int): Maximum findings to return.

    Returns:
        dict[str, Any]: Findings, the total before truncation, and counts by
        code so the UI can offer facets without a second request.
    """
    engine = _engine()
    map_ = await asyncio.to_thread(engine.graph)
    selected = [
        f
        for f in map_.findings
        if (severity is None or f.severity == severity) and (code is None or f.code == code)
    ]
    by_code: dict[str, int] = {}
    for finding in map_.findings:
        by_code[finding.code] = by_code.get(finding.code, 0) + 1
    return {
        "total": len(selected),
        "by_code": dict(sorted(by_code.items(), key=lambda kv: -kv[1])),
        "findings": [f.to_dict() for f in selected[:limit]],
    }


@router.post("/sync")
async def post_sync(full: bool = False, delta: bool = True, _auth=Depends(verify_api_key)) -> dict[str, Any]:
    """Re-scan the project and republish the graph.

    Args:
        full (bool): Discard stored state and re-extract everything.
        delta (bool): Include a before/after delta in the report.

    Returns:
        dict[str, Any]: The sync report, or ``{"busy": true}`` when another
        sync is already running.
    """
    if not _sync_lock.acquire(blocking=False):
        return {"busy": True, "detail": "A sync is already running."}
    try:
        engine = _engine()
        report = await asyncio.to_thread(engine.sync, full, delta)
        return {"busy": False, **report.to_dict()}
    finally:
        _sync_lock.release()


@router.post("/export")
async def post_export(_auth=Depends(verify_api_key)) -> dict[str, Any]:
    """Write the Obsidian vault to the path configured in the profile.

    Returns:
        dict[str, Any]: Note counts and the vault location.
    """
    engine = _engine()
    map_ = await asyncio.to_thread(engine.graph)
    if not map_.nodes:
        raise HTTPException(status_code=409, detail="No map to export — run a sync first.")
    return await asyncio.to_thread(
        ObsidianVaultExporter().export, map_, engine.profile.resolved_vault_path()
    )
