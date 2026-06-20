from fastapi import APIRouter

router = APIRouter(tags=["data"])


@router.get("/api/v1/overview")
async def get_overview():
    from cherenkov.ai.accounting import CostAccountant
    from cherenkov.core.feedback_store import FeedbackStore

    accountant = CostAccountant()
    kpi = accountant.get_governance_kpis()
    feedback = FeedbackStore()
    recent = feedback.get_all()[-10:] if feedback.get_all() else []

    return {
        "falsePositiveRate": kpi["false_positive_rate"],
        "maintenanceEfficiency": kpi["maintenance_efficiency"],
        "defectEscapeCount": kpi["defect_escape_count"],
        "totalVerdicts": kpi["total_verdicts"],
        "recentLearnings": [
            {
                "id": f.hitl_item_id,
                "action": f.action,
                "reason": f.reason,
                "timestamp": getattr(f, "timestamp", ""),
            }
            for f in recent
        ],
    }


@router.get("/api/v1/truth-map")
async def get_truth_map():
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()
    try:
        idioms = store.get_idioms(limit=50)
    except Exception:
        idioms = []
    return [
        {
            "id": i.id,
            "pattern": i.pattern,
            "divergence_class": i.divergence_class.value
            if i.divergence_class
            else "unknown",
            "endpoint": i.endpoint,
            "confirm_count": i.confirm_count,
            "decay_score": i.decay_score,
        }
        for i in idioms
    ]


@router.get("/api/v1/failures")
async def get_failures():
    from cherenkov.reflector.store import VerdictStore
    from cherenkov.core.contracts import VerdictOutcome

    _FAILURE_TYPE_MAP = {
        "CONTRACT_DRIFT": "CONTRACT_DRIFT",
        "AUTH_EXPIRY": "AUTH_EXPIRY",
        "STATE_SEQUENCING": "STATE_SEQUENCING",
        "NETWORK_FLAKY": "NETWORK_FLAKY",
        "ASSERTION_DRIFT": "ASSERTION_DRIFT",
    }

    store = VerdictStore()
    reject_val = VerdictOutcome.REJECT.value
    escaped_val = VerdictOutcome.ESCAPED_DEFECT.value

    def _query_failures():
        import sqlite3

        conn = sqlite3.connect(store.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT id, endpoint, outcome, failure_class, detail, timestamp "
                "FROM verdicts WHERE outcome IN (?, ?) "
                "ORDER BY timestamp DESC LIMIT 50",
                (reject_val, escaped_val),
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    import asyncio
    raw = await asyncio.to_thread(_query_failures)

    return [
        {
            "id": r["id"],
            "name": r["endpoint"] or r["id"],
            "failureType": _FAILURE_TYPE_MAP.get(
                r.get("failure_class") or "", "ASSERTION_DRIFT"
            ),
            "diagnosis": r.get("detail") or "Failure detected during review.",
            "oldCode": "",
            "proposedCode": "",
            "hasAssertionWarning": False,
            "endpoint": r["endpoint"],
            "outcome": r["outcome"],
            "timestamp": r["timestamp"],
        }
        for r in raw
    ]


@router.get("/api/v1/memory")
async def get_memory():
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()
    try:
        raw_idioms = store.get_idioms(limit=50)
    except Exception:
        raw_idioms = []

    idioms = [
        {
            "id": i.id,
            "text": i.pattern,
            "count": i.confirm_count,
            "decay": f"{i.decay_score:.0%}" if i.decay_score is not None else "ACTIVE",
        }
        for i in raw_idioms
    ]
    pairing = [
        {
            "context": "API conformance",
            "explanation": "Verify status codes, response schemas, and auth flows match the OpenAPI spec before approving a test.",
        },
        {
            "context": "False positive triage",
            "explanation": "When a test fails, cross-check the spec claim and actual response body to determine if the spec or the implementation is wrong.",
        },
    ]
    return {"idioms": idioms, "pairing": pairing}


@router.get("/api/v1/signals")
async def get_signals():
    from cherenkov.ai.accounting import CostAccountant
    from cherenkov.reflector.store import VerdictStore

    store = VerdictStore()

    def _query_signals():
        import sqlite3

        conn = sqlite3.connect(store.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT endpoint, duration_ms, timestamp FROM verdicts ORDER BY timestamp DESC LIMIT 20"
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    import asyncio
    performance = []
    for r in await asyncio.to_thread(_query_signals):
        dur = r["duration_ms"] if r["duration_ms"] else 0
        baseline = 200
        performance.append(
            {
                "time": r["timestamp"] or "",
                "latency": dur,
                "baseline": baseline,
                "anomaly": dur > baseline * 3,
            }
        )

    visual = [
        {"id": "v1", "name": "Overview Dashboard", "difference": "0.0%", "status": "ok"},
        {"id": "v2", "name": "Divergences Table", "difference": "0.0%", "status": "ok"},
    ]

    accountant = CostAccountant()
    report = accountant.report
    total = report.request_count or 1
    coverage = [
        {
            "path": "/api/v1/*",
            "cherenkov": min(100, round((report.request_count / max(total, 1)) * 100)),
            "sdet": 0,
        },
    ]

    return {"performance": performance, "visual": visual, "coverage": coverage}
