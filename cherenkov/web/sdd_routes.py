"""
SDD Agent Cockpit API — bridges agent_memory/sync/ JSON files to the dashboard.
Read-only by default (Sprint 1). Write endpoints added in Sprint 2.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from cherenkov.web.sdd_models import (
    SddSession,
    SddTokenData,
    TokenSnapshot,
    TokenHistory,
    TaskTypeStats,
    SddContextData,
    ContextSnippet,
    GraphStatus,
    GraphData,
    GraphNode,
    GraphEdge,
    WikiEntry,
    PatternInsight,
    CompactResult,
)

router = APIRouter(tags=["sdd"])

SYNC_DIR = Path("agent_memory/sync")
FINDINGS_DIR = SYNC_DIR / "findings"
MEMORY_DIR = Path("agent_memory")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Session Endpoints ──────────────────────────────────────────────────


@router.get("/api/v1/sdd/status")
async def get_sdd_status():
    session, tokens, exp = await asyncio.gather(
        asyncio.to_thread(_read_json, SYNC_DIR / "session.json"),
        asyncio.to_thread(_read_json, SYNC_DIR / "tokens.json"),
        asyncio.to_thread(_read_json, SYNC_DIR / "experience.json"),
    )
    s = session.get("session", {})
    tok = tokens.get("current_session", {})
    hist = tokens.get("historical", {})
    return {
        "session": s,
        "current_tokens": tok,
        "budget": tokens.get("budget", {}),
        "historical": hist,
        "experience_count": exp.get("experience_count", 0),
        "sessions_since_compact": session.get("sessions_since_compact", 0),
    }


@router.get("/api/v1/sdd/sessions")
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    task_type: str | None = None,
):
    session = await asyncio.to_thread(_read_json, SYNC_DIR / "session.json")
    prev = session.get("previous_sessions", [])
    current = session.get("session", {})
    result = []
    if current and current.get("id") and current["id"] != "sess_init":
        result.append(_coerce_session(current))
    for p in reversed(prev[-limit:]):
        result.append(
            SddSession(
                id=p.get("id", ""),
                status="closed",
                task=p.get("task"),
                token_total=p.get("token_total", 0),
                summary=p.get("summary"),
                started_at=_parse_dt(p.get("started_at")),
                ended_at=_parse_dt(p.get("ended_at")),
            ).model_dump()
        )
    if task_type:
        result = [
            s
            for s in result
            if s.get("task_type") == task_type or s.get("task") == task_type
        ]
    return result[:limit]


@router.get("/api/v1/sdd/sessions/{session_id}")
async def get_session_detail(session_id: str):
    session = await asyncio.to_thread(_read_json, SYNC_DIR / "session.json")
    s = session.get("session", {})
    if s.get("id") == session_id:
        findings = await asyncio.to_thread(_read_json, FINDINGS_DIR / f"{session_id}.json")
        return {
            "session": _coerce_session(s).model_dump(),
            "findings": findings.get("findings", []),
        }
    for p in session.get("previous_sessions", []):
        if p.get("id") == session_id:
            findings = await asyncio.to_thread(_read_json, FINDINGS_DIR / f"{session_id}.json")
            return {
                "session": {
                    "id": p["id"],
                    "status": "closed",
                    "task": p.get("task"),
                    "token_total": p.get("token_total", 0),
                    "summary": p.get("summary"),
                    "findings_count": p.get("findings_count", 0),
                    "started_at": p.get("started_at"),
                    "ended_at": p.get("ended_at"),
                },
                "findings": findings.get("findings", []),
            }
    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


# ── Token Endpoints ────────────────────────────────────────────────────


@router.get("/api/v1/sdd/tokens")
async def get_token_data():
    raw = await asyncio.to_thread(_read_json, SYNC_DIR / "tokens.json")
    cur = raw.get("current_session", {})
    hist = raw.get("historical", {})
    by_type = {}
    for k, v in hist.get("by_task_type", {}).items():
        by_type[k] = TaskTypeStats(
            sessions=v.get("sessions", 0), total_tokens=v.get("total_tokens", 0)
        )
    return SddTokenData(
        current_session=TokenSnapshot(
            session_id=cur.get("session_id"),
            prompt=cur.get("prompt", 0),
            generate=cur.get("generate", 0),
            read=cur.get("read", 0),
            search=cur.get("search", 0),
            total=cur.get("total", 0),
        ),
        budget=raw.get("budget", {}),
        historical=TokenHistory(
            total_all_time=hist.get("total_all_time", 0),
            sessions_completed=hist.get("sessions_completed", 0),
            avg_per_session=hist.get("avg_per_session", 0.0),
            by_task_type=by_type,
        ),
        top_consumers=raw.get("top_consumers", []),
    ).model_dump()


@router.get("/api/v1/sdd/tokens/history")
async def get_token_history():
    tokens = await asyncio.to_thread(_read_json, SYNC_DIR / "tokens.json")
    return tokens.get("historical", {})


# ── Experience Endpoints ────────────────────────────────────────────────


@router.get("/api/v1/sdd/experience")
async def list_experience(
    pattern: str | None = None,
    outcome: str | None = None,
    sort: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    raw = await asyncio.to_thread(_read_json, SYNC_DIR / "experience.json")
    results = list(raw.get("experiences", []))
    if pattern:
        pl = pattern.lower()
        results = [
            r
            for r in results
            if pl in " ".join(r.get("patterns", [])).lower()
            or pl in r.get("action", "").lower()
        ]
    if outcome:
        results = [r for r in results if r.get("outcome") == outcome]
    if sort == "cost":
        results.sort(key=lambda r: r.get("token_cost", 0), reverse=True)
    elif sort == "date":
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return results[:limit]


@router.get("/api/v1/sdd/experience/{exp_id}")
async def get_experience_detail(exp_id: str):
    raw = await asyncio.to_thread(_read_json, SYNC_DIR / "experience.json")
    for r in raw.get("experiences", []):
        if r.get("id") == exp_id:
            return r
    raise HTTPException(status_code=404, detail=f"Experience {exp_id} not found")


# ── Context Endpoints ────────────────────────────────────────────────────


@router.get("/api/v1/sdd/context")
async def get_context():
    raw = await asyncio.to_thread(_read_json, SYNC_DIR / "context.json")
    snippets = [ContextSnippet(**s) for s in raw.get("snippets", [])]
    return SddContextData(
        version=raw.get("version", 1),
        last_refreshed=raw.get("last_refreshed", ""),
        snippets=snippets,
        task_type_map=raw.get("task_type_map", {}),
    ).model_dump()


# ── Compact Endpoint ─────────────────────────────────────────────────────


@router.post("/api/v1/sdd/compact")
async def trigger_compact(force: bool = False):
    context, session = await asyncio.gather(
        asyncio.to_thread(_read_json, SYNC_DIR / "context.json"),
        asyncio.to_thread(_read_json, SYNC_DIR / "session.json"),
    )
    snippets = context.get("snippets", [])
    ssc = session.get("sessions_since_compact", 0)
    if ssc < 3 and not force:
        return CompactResult(
            sessions_since=ssc,
            snippets_before=len(snippets),
            snippets_after=len(snippets),
            promoted=0,
            archived=0,
        ).model_dump()
    session["sessions_since_compact"] = 0
    context["last_refreshed"] = _timestamp()
    await asyncio.gather(
        asyncio.to_thread(_write_json, SYNC_DIR / "context.json", context),
        asyncio.to_thread(_write_json, SYNC_DIR / "session.json", session),
    )
    return CompactResult(
        sessions_since=ssc,
        snippets_before=len(snippets),
        snippets_after=len(snippets),
        promoted=0,
        archived=0,
    ).model_dump()


# ── Graph Endpoints (stub — Sprint 3 fills these) ───────────────────────


@router.get("/api/v1/sdd/graph/status")
async def get_graph_status():
    exp, session = await asyncio.gather(
        asyncio.to_thread(_read_json, SYNC_DIR / "experience.json"),
        asyncio.to_thread(_read_json, SYNC_DIR / "session.json"),
    )
    return GraphStatus(
        node_count=exp.get("experience_count", 0) + 2,
        edge_count=exp.get("experience_count", 0),
        session_count=session.get("previous_sessions", []).__len__() + 1,
        experience_count=exp.get("experience_count", 0),
    ).model_dump()


@router.get("/api/v1/sdd/graph/export")
async def export_graph():
    exp = await asyncio.to_thread(_read_json, SYNC_DIR / "experience.json")
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    session_ids = set()
    for e in exp.get("experiences", []):
        sid = e.get("session_id", "")
        if sid and sid not in session_ids:
            session_ids.add(sid)
            nodes.append(
                GraphNode(
                    id=sid, type="session", label=sid[:20], color="#06b6d4", size=1.5
                )
            )
        eid = e.get("id", "")
        nodes.append(
            GraphNode(
                id=eid,
                type="experience",
                label=e.get("action", "")[:40],
                color="#10b981",
                size=1.0,
            )
        )
        if sid:
            edges.append(
                GraphEdge(source=sid, target=eid, type="has_experience", weight=1.0)
            )
    return GraphData(nodes=nodes, edges=edges).model_dump()


@router.get("/api/v1/sdd/graph/patterns")
async def get_pattern_insights():
    exp = await asyncio.to_thread(_read_json, SYNC_DIR / "experience.json")
    pattern_map: dict[str, dict[str, Any]] = {}
    for e in exp.get("experiences", []):
        for p in e.get("patterns", []):
            if p not in pattern_map:
                pattern_map[p] = {
                    "count": 0,
                    "successes": 0,
                    "total_cost": 0.0,
                    "ids": [],
                }
            pattern_map[p]["count"] += 1
            if e.get("outcome") == "success":
                pattern_map[p]["successes"] += 1
            pattern_map[p]["total_cost"] += e.get("token_cost", 0)
            pattern_map[p]["ids"].append(e.get("id", ""))
    results = []
    for name, data in pattern_map.items():
        results.append(
            PatternInsight(
                name=name,
                frequency=data["count"],
                success_rate=data["successes"] / data["count"]
                if data["count"]
                else 0.0,
                avg_token_cost=data["total_cost"] / data["count"]
                if data["count"]
                else 0.0,
                experience_ids=data["ids"][:10],
            ).model_dump()
        )
    results.sort(key=lambda r: r["frequency"], reverse=True)
    return results


# ── Wiki Endpoints (stub — Sprint 4 fills these fully) ──────────────────


def _scan_wiki_tree() -> list[dict]:
    if not MEMORY_DIR.exists():
        return []
    entries = []
    for f in sorted(MEMORY_DIR.rglob("*.md")):
        rel = f.relative_to(MEMORY_DIR)
        stat = f.stat()
        entries.append(
            WikiEntry(
                path=str(rel).replace("\\", "/"),
                title=f.stem.replace("-", " ").title(),
                size=stat.st_size,
                last_updated=datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat()
                if hasattr(stat, "st_mtime")
                else "",
            ).model_dump()
        )
    return entries


@router.get("/api/v1/sdd/wiki/tree")
async def get_wiki_tree():
    return await asyncio.to_thread(_scan_wiki_tree)


def _read_wiki_file(path: str) -> dict[str, Any]:
    full = (MEMORY_DIR / path).resolve()
    if not full.exists() or not full.is_file():
        raise FileNotFoundError(path)
    if not str(full).startswith(str(MEMORY_DIR.resolve())):
        raise PermissionError(path)
    content = full.read_text(encoding="utf-8")
    stat = full.stat()
    return {
        "path": path,
        "content": content,
        "size": stat.st_size,
        "last_updated": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()
        if hasattr(stat, "st_mtime")
        else "",
    }


@router.get("/api/v1/sdd/wiki/{path:path}")
async def get_wiki_file(path: str):
    try:
        return await asyncio.to_thread(_read_wiki_file, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Wiki file {path} not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Path traversal blocked")


# ── Findings Endpoint ────────────────────────────────────────────────────


def _load_all_findings(limit: int) -> list[dict]:
    all_findings = []
    for fpath in sorted(FINDINGS_DIR.glob("sess_*.json")):
        data = _read_json(fpath)
        for f in data.get("findings", []):
            f["_session_id"] = data.get("session_id", fpath.stem)
            all_findings.append(f)
    all_findings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return all_findings[:limit]


@router.get("/api/v1/sdd/findings")
async def list_findings(
    session_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    if session_id:
        fpath = FINDINGS_DIR / f"{session_id}.json"
        data = await asyncio.to_thread(_read_json, fpath)
        return data.get("findings", [])[:limit]
    return await asyncio.to_thread(_load_all_findings, limit)


# ── Helpers ──────────────────────────────────────────────────────────────


def _coerce_session(s: dict) -> SddSession:
    return SddSession(
        id=s.get("id", ""),
        status=s.get("status", "unknown"),
        task=s.get("task"),
        task_type=s.get("task_type"),
        started_at=_parse_dt(s.get("started_at")),
        ended_at=_parse_dt(s.get("ended_at")),
        findings_count=s.get("findings_count", 0),
        token_total=s.get("token_total", 0),
        summary=s.get("summary"),
        compacted=s.get("compacted", False),
    )


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None
