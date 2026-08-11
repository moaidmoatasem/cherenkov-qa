"""FastAPI routes for enterprise compliance (GDPR, SOC2, Org, SLA, Support)."""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cherenkov.enterprise.gdpr import get_gdpr, GDPRConfig
from cherenkov.enterprise.soc2 import get_soc2
from cherenkov.enterprise.org import OrgManager

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])

# Note: In a real environment, OrgManager might be backed by a DB.
# Here we initialize a mock instance for demonstration in the dashboard.
_org_manager = OrgManager()

DEFAULT_ORG_NAME = "Cherenkov Enterprise"
DEFAULT_ORG_OWNER_ID = "admin-1"

# How many recent runs the SLA view aggregates over.
_SLA_WINDOW = 500

@router.get("/gdpr/status")
def gdpr_status() -> Dict[str, Any]:
    """Return GDPR compliance configuration and status.

    Returns:
        Dictionary payload listing GDPR enabled state and configuration settings.
    """
    gdpr = get_gdpr()
    return {
        "enabled": gdpr.is_enabled(),
        "config": {
            "data_retention": gdpr.config.data_retention.value,
            "anonymize_on_delete": gdpr.config.anonymize_on_delete,
            "consent_required": gdpr.config.consent_required,
        }
    }

@router.post("/gdpr/purge")
def gdpr_purge() -> Dict[str, Any]:
    """Purge expired customer data in compliance with GDPR retention policy.

    Returns:
        Dictionary status payload and count of purged records.
    """
    gdpr = get_gdpr()
    purged = gdpr.purge_old_data()
    return {"status": "success", "purged_records": purged}

@router.get("/soc2/report")
def soc2_report() -> Dict[str, Any]:
    """Generate and return a SOC2 audit compliance report.

    Returns:
        Dictionary payload containing SOC2 compliance report fields.
    """
    soc2 = get_soc2()
    # Generate a fresh report just in time
    report = soc2.generate_report(organization=DEFAULT_ORG_NAME)
    return report.__dict__

@router.get("/soc2/summary")
def soc2_summary() -> Dict[str, Any]:
    """Return executive summary of SOC2 control evaluations.

    Returns:
        Compliance summary dictionary.
    """
    soc2 = get_soc2()
    return soc2.get_compliance_summary()

@router.get("/org")
def org_info() -> Dict[str, Any]:
    """Return organization details and quota limits.

    Returns:
        Dictionary containing organization ID, tier, member count, and user quotas.
    """
    # OrgManager assigns a generated `org_<uuid>` id, so the default org has to be
    # looked up by name — there is no fixed id to fetch it by. Doing it this way also
    # keeps the endpoint idempotent: without the lookup it would mint a new
    # organization on every request.
    org = next((o for o in _org_manager.list_orgs() if o.name == DEFAULT_ORG_NAME), None)
    if org is None:
        org = _org_manager.create_org(DEFAULT_ORG_NAME, DEFAULT_ORG_OWNER_ID)
    return {
        "id": org.id,
        "name": org.name,
        "tier": org.tier,
        "members": len(org.members),
        "quota_max_users": org.quota_max_users
    }

@router.get("/sla")
def sla_dashboard() -> Dict[str, Any]:
    """Return enterprise SLA uptime and performance metrics.

    Returns:
        SLA metrics dictionary including uptime, p99 latency, and check counts.
    """
    # Derived from persisted RunRecords. This endpoint previously returned five
    # hardcoded constants (uptime 99.99, p99 145ms, 125000 checks, 12 failures,
    # "operational") with no indication to the caller that none of it was measured.
    #
    # Note there is deliberately no `uptime` field any more. CHERENKOV does not
    # monitor availability of anything, so an uptime percentage could only ever be
    # invented; `pass_rate_pct` is the thing it actually measures. Renaming rather
    # than re-deriving avoids swapping one fabrication for a subtler one.
    from cherenkov.persistence.run_store import get_run_store
    from cherenkov.web.coverage_map import conformance_summary

    store = get_run_store()
    records = store.list(limit=_SLA_WINDOW)
    summary = conformance_summary(store=store)

    total = summary["totalRuns"]
    durations = sorted(r.duration_ms for r in records if r.duration_ms > 0)
    p99 = durations[min(int(len(durations) * 0.99), len(durations) - 1)] if durations else None

    latest = (summary["latestVerdict"] or "").upper()
    status = {
        "PASS": "operational",
        "CERTIFIED": "operational",
        "WARN": "degraded",
        "FAIL": "failing",
    }.get(latest, "no_data")

    return {
        # False when no run has been recorded yet, so a caller can render an empty
        # state instead of showing zeros that look like measurements.
        "measured": total > 0,
        "source": "run_store",
        "total_checks": total,
        "failed_checks": summary["failCount"],
        "pass_rate_pct": round(100.0 * summary["passCount"] / total, 2) if total else None,
        "api_response_p99": p99,
        "latest_verdict": summary["latestVerdict"],
        "status": status,
        # Real per-run history for the trend chart, newest last.
        "trend": summary["trend"],
    }

@router.post("/support/ticket")
def create_support_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a priority enterprise support ticket.

    Args:
        payload: Ticket content dictionary.

    Returns:
        Dictionary status payload including generated ticket ID.
    """
    # There is no support-portal integration. This used to mint a random UUID and
    # answer "Enterprise support team has been notified." — a false assurance about
    # an action that never happened, which is worse than fabricated data: a user who
    # believed it would not escalate through a channel that actually reaches anyone.
    #
    # 501 until a real backend is wired (#763). Returning an error is the honest
    # answer to a capability that does not exist.
    raise HTTPException(
        status_code=501,
        detail=(
            "Support ticketing is not wired to a backend. No ticket was created and "
            "nobody was notified. Open an issue at "
            "https://github.com/moaidmoatasem/cherenkov-qa/issues instead."
        ),
    )
