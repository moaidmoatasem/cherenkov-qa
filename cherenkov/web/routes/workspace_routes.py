from fastapi import APIRouter, Depends

from cherenkov.web.routes.deps import verify_api_key

router = APIRouter(tags=["workspace"])

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

_SETTINGS_PROTECTED_FIELDS = {"security": {"auth_secret", "egress_policy"}}


@router.get("/api/v1/settings")
async def api_get_settings(_auth=Depends(verify_api_key)):
    redacted = {
        k: (dict(v) if isinstance(v, dict) else v) for k, v in _settings.items()
    }
    if "auth_secret" in redacted.get("security", {}):
        redacted["security"]["auth_secret"] = (
            "***" if redacted["security"]["auth_secret"] else ""
        )
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
        issues.append(
            {
                "id": "high-fp",
                "severity": "high",
                "message": f"False positive rate {fp_rate:.1%} exceeds 5% threshold",
            }
        )
    return {
        "score": score,
        "issues": issues,
        "defectEscapeRate": kpi.get("defect_escape_rate", 0.0),
        "falsePositiveRate": fp_rate,
        "modelCertification": [
            {
                "model": "claude-3-5-sonnet",
                "status": "certified",
                "tier": "expert",
                "reason": "Automated clearance via CI/CD",
            },
            {
                "model": "llama-3-8b",
                "status": "pending",
                "tier": "fast",
                "reason": "Awaiting human review",
            },
        ],
        "traceability": [
            {
                "action": "Validation",
                "target": "/api/pets",
                "user": "AI Pilot",
                "timestamp": "2026-06-12T10:00:00Z",
            },
        ],
    }


@router.get("/api/v1/projects")
async def get_projects():
    import os
    import asyncio
    import sqlite3
    from cherenkov.reflector.store import VerdictStore

    workspace = os.getcwd()
    store = VerdictStore()

    def _query_projects():
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
