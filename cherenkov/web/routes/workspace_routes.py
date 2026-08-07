from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cherenkov.core.settings import get_settings, reset_settings
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role
from cherenkov.web.routes.deps import verify_api_key

router = APIRouter(tags=["workspace"])

# ── Project persistence ────────────────────────────────────────────────────────

_PROJECTS_DB = Path(os.getcwd()) / ".cherenkov" / "projects.db"


def _db():
    _PROJECTS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_PROJECTS_DB, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            target_url TEXT DEFAULT '',
            spec_path TEXT DEFAULT '',
            repo_type TEXT DEFAULT 'new',
            repo_path TEXT DEFAULT '',
            status TEXT DEFAULT 'queued',
            created_at TEXT DEFAULT (datetime('now')),
            run_count INTEGER DEFAULT 0,
            pass_rate INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


class NewProjectPayload(BaseModel):
    name: str
    target_url: str = ''
    spec_path: str = ''
    repo_type: str = 'new'
    repo_path: str = ''

_ENV_PATH = Path(os.getcwd()) / ".env"


def _load_env() -> dict[str, str]:
    if not _ENV_PATH.exists():
        return {}
    data: dict[str, str] = {}
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _write_env_var(key: str, value: str) -> None:
    env = _load_env()
    env[key] = value
    lines = [f'{k}="{v}"' for k, v in env.items()]
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _settings_payload(settings) -> dict:
    """Truthful settings snapshot — every value maps to a real CherenkovSettings field."""
    return {
        "model": settings.PROVIDER,
        "target": {"url": settings.API_URL},
        "security": {"egress_policy": settings.EGRESS},
        "airllm": {
            "enabled": settings.AIRLLM_ENABLED,
            "model": settings.AIRLLM_MODEL,
            "compression": settings.AIRLLM_COMPRESSION,
            "layer_shards_path": settings.AIRLLM_LAYER_SHARDS_PATH,
        },
        "vlm": {
            "provider": settings.VLM_DEFAULT_PROVIDER,
            "model": settings.VLM_LOCALAI_MODEL,
            "ocr_enabled": settings.OCR_ENABLED,
        },
    }


def _persist_settings_to_env(body: dict) -> None:
    provider = body.get("model")
    if provider:
        _write_env_var("PROVIDER", provider)

    target = body.get("target")
    if isinstance(target, dict) and target.get("url"):
        _write_env_var("API_URL", str(target["url"]))

    security = body.get("security")
    if isinstance(security, dict) and security.get("egress_policy"):
        _write_env_var("CHERENKOV_EGRESS", str(security["egress_policy"]))

    airllm = body.get("airllm")
    if isinstance(airllm, dict):
        if "enabled" in airllm:
            _write_env_var("CHERENKOV_AIRLLM_ENABLED", "true" if airllm["enabled"] else "false")
        if "model" in airllm:
            _write_env_var("CHERENKOV_AIRLLM_MODEL", str(airllm["model"]))
        if "compression" in airllm:
            _write_env_var("CHERENKOV_AIRLLM_COMPRESSION", str(airllm["compression"]))
        if "layer_shards_path" in airllm:
            _write_env_var("CHERENKOV_AIRLLM_LAYER_SHARDS_PATH", str(airllm["layer_shards_path"]))


@router.get("/api/v1/settings")
async def api_get_settings(_auth=Depends(verify_api_key)):
    """Return real settings from CherenkovSettings, not mock data."""
    settings = get_settings()
    payload = _settings_payload(settings)
    # Force reload from .env on the next fetch so external edits take effect.
    reset_settings()
    return payload


@router.put("/api/v1/settings")
async def update_settings(body: dict, _auth=Depends(verify_api_key), _role=Depends(require_role(Role.admin))):
    """Persist the supported settings to .env and return the updated configuration."""
    _persist_settings_to_env(body)

    # Force reload on next GET
    reset_settings()

    # Return the updated settings, reflecting what was just accepted.
    settings = get_settings()
    payload = _settings_payload(settings)

    if body.get("model"):
        payload["model"] = str(body["model"])
    target = body.get("target")
    if isinstance(target, dict) and target.get("url"):
        payload["target"] = {"url": str(target["url"])}
    security = body.get("security")
    if isinstance(security, dict) and security.get("egress_policy"):
        payload["security"] = {"egress_policy": str(security["egress_policy"])}
    airllm = body.get("airllm")
    if isinstance(airllm, dict):
        for key in ("enabled", "model", "compression", "layer_shards_path"):
            if key in airllm:
                payload["airllm"][key] = airllm[key]
    return payload


@router.get("/api/v1/governance")
async def get_governance():
    from cherenkov.substrate.accounting import CostAccountant
    accountant = CostAccountant()
    kpi = accountant.get_governance_kpis()
    fp_rate = kpi.get("false_positive_rate", 0.0)
    score = max(0, round(100 - fp_rate * 100))
    issues = []
    if fp_rate > 0.05:
        issues.append({
            "id": "high-fp", "severity": "high",
            "message": f"False positive rate {fp_rate:.1%} exceeds 5% threshold",
        })
    return {
        "score": score, "issues": issues,
        "defectEscapeRate": kpi.get("defect_escape_rate", 0.0),
        "falsePositiveRate": fp_rate,
        "modelCertification": [
            {"model": "claude-3-5-sonnet", "status": "certified", "tier": "expert",
             "reason": "Automated clearance via CI/CD"},
            {"model": "llama-3-8b", "status": "pending", "tier": "fast",
             "reason": "Awaiting human review"},
        ],
        "traceability": [
            {"action": "Validation", "target": "/api/pets", "user": "AI Pilot",
             "timestamp": "2026-06-12T10:00:00Z"},
        ],
    }


@router.get("/api/v1/projects")
async def get_projects():
    def _query():
        conn = _db()
        try:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    rows = await asyncio.to_thread(_query)

    # Always include the workspace default if no projects exist
    if not rows:
        workspace = os.getcwd()
        return [{
            "id": "default",
            "name": os.path.basename(workspace) or "cherenkov-qa",
            "target_url": "",
            "spec_path": "",
            "repo_type": "existing",
            "repo_path": workspace,
            "status": "queued",
            "created_at": "",
            "run_count": 0,
            "pass_rate": 0,
            "lastRun": "",
            "pipelineStatus": {"ingest": "queued", "plan": "queued", "generate": "queued", "review": "queued"},
            "stats": {"testsCount": 0, "passRate": 0, "healingCount": 0},
            "sparkline": [],
        }]

    return [
        {
            **row,
            "lastRun": row.get("created_at", ""),
            "pipelineStatus": {"ingest": "done" if row["spec_path"] else "queued", "plan": "queued", "generate": "queued", "review": "queued"},
            "stats": {"testsCount": row["run_count"], "passRate": row["pass_rate"], "healingCount": 0},
            "sparkline": [],
        }
        for row in rows
    ]

@router.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    def _query():
        conn = _db()
        try:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    row = await asyncio.to_thread(_query)
    if not row:
        if project_id == "default":
            workspace = os.getcwd()
            return {
                "id": "default",
                "name": os.path.basename(workspace) or "cherenkov-qa",
                "target_url": "",
                "spec_path": "",
                "repo_type": "existing",
                "repo_path": workspace,
                "status": "queued",
                "created_at": "",
                "run_count": 0,
                "pass_rate": 0,
                "lastRun": "",
                "pipelineStatus": {"ingest": "queued", "plan": "queued", "generate": "queued", "review": "queued"},
                "stats": {"testsCount": 0, "passRate": 0, "healingCount": 0},
                "sparkline": [],
            }
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        **row,
        "lastRun": row.get("created_at", ""),
        "pipelineStatus": {"ingest": "done", "plan": "done", "generate": "done", "review": "pending"},
        "stats": {"testsCount": row.get("run_count", 0), "passRate": row.get("pass_rate", 0), "healingCount": 0},
        "sparkline": [],
    }

@router.post("/api/v1/projects")
async def create_project(payload: NewProjectPayload, _role=Depends(require_role(Role.reviewer))):
    project_id = str(uuid.uuid4())[:8]

    def _insert():
        conn = _db()
        try:
            conn.execute(
                "INSERT INTO projects (id, name, target_url, spec_path, repo_type, repo_path) VALUES (?,?,?,?,?,?)",
                (project_id, payload.name, payload.target_url, payload.spec_path, payload.repo_type, payload.repo_path)
            )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_insert)
    return {
        "id": project_id,
        "name": payload.name,
        "target_url": payload.target_url,
        "spec_path": payload.spec_path,
        "repo_type": payload.repo_type,
        "repo_path": payload.repo_path,
        "status": "queued",
        "lastRun": "",
        "pipelineStatus": {"ingest": "done" if payload.spec_path else "queued", "plan": "queued", "generate": "queued", "review": "queued"},
        "stats": {"testsCount": 0, "passRate": 0, "healingCount": 0},
        "sparkline": [],
    }


@router.patch("/api/v1/projects/{project_id}")
async def update_project(project_id: str, payload: dict, _role=Depends(require_role(Role.reviewer))):
    allowed = {"name", "target_url", "spec_path", "repo_type", "repo_path", "status", "run_count", "pass_rate"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    def _update():
        conn = _db()
        try:
            sets = ", ".join(f"{k}=?" for k in updates)
            vals = [*updates.values(), project_id]
            conn.execute(f"UPDATE projects SET {sets} WHERE id=?", vals)
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_update)
    return {"id": project_id, **updates}
