import asyncio
import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cherenkov.web.routes.deps import verify_api_key

router = APIRouter(tags=["workspace"])

# ── Project persistence ────────────────────────────────────────────────────────

_PROJECTS_DB = Path(os.getcwd()) / ".cherenkov" / "projects.db"


def _db():
    _PROJECTS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_PROJECTS_DB), timeout=5.0)
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

_settings: dict = {
    "target": {"url": "http://localhost:8000", "auth_header": ""},
    "engine": {
        "model_tier": "local", "enable_demo_mode": False,
        "execution_budget": 100, "workers": 4,
    },
    "security": {"egress_policy": "strict", "auth_secret": ""},
    "ui": {"density": "comfortable", "reduced_motion": False},
}

_SETTINGS_PROTECTED_FIELDS = {"security": {"auth_secret", "egress_policy"}}


@router.get("/api/v1/settings")
async def api_get_settings(_auth=Depends(verify_api_key)):
    redacted = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _settings.items()}
    if "auth_secret" in redacted.get("security", {}):
        redacted["security"]["auth_secret"] = "***" if redacted["security"]["auth_secret"] else ""
    return redacted


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


@router.get("/api/v1/governance")
async def get_governance():
    from cherenkov.ai.accounting import CostAccountant
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


@router.post("/api/v1/projects")
async def create_project(payload: NewProjectPayload):
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
async def update_project(project_id: str, payload: dict):
    allowed = {"name", "target_url", "spec_path", "repo_type", "repo_path", "status", "run_count", "pass_rate"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    def _update():
        conn = _db()
        try:
            sets = ", ".join(f"{k}=?" for k in updates)
            vals = list(updates.values()) + [project_id]
            conn.execute(f"UPDATE projects SET {sets} WHERE id=?", vals)
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_update)
    return {"id": project_id, **updates}
