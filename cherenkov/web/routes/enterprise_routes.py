"""FastAPI routes for enterprise compliance (GDPR, SOC2, Org, run statistics).

The support-ticket endpoint that used to live here was removed rather than
implemented: it returned a UUID and the message "Enterprise support team has
been notified" while persisting nothing and sending nothing, and per the
no-paid-tier product decision on #754 there is no support team to route to. No
implementation could have made that message true.
"""
from __future__ import annotations

import calendar
import os
import time
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
def sla_dashboard(days: int = 30) -> Dict[str, Any]:
    """Return run statistics measured from the local run store.

    Every figure here is counted from `RunStore`. Two metrics that used to
    appear on this endpoint have been removed rather than estimated:

      * **uptime** — CHERENKOV runs conformance checks against a target on
        demand; it is not a monitor and never observes the target between runs,
        so it cannot know its uptime.
      * **API response p99** — the run store records how long a CHERENKOV *run*
        took, which is not the target API's response latency.

    Both were previously served as hardcoded constants (99.99% and 145 ms)
    beneath a "Target: 99.9%" label. Reporting an unmeasured number as an
    observation is the exact failure this project exists to detect.

    Args:
        days: Size of the trailing window, in days.

    Returns:
        Counts over the window, plus a per-day series with one entry per day.
    """
    from cherenkov.persistence.run_store import get_run_store

    cutoff = time.time() - days * 86_400
    # `list` is capped; ask for far more than a local store is expected to hold
    # so the window is not silently truncated.
    runs = get_run_store().list(limit=100_000)

    def _epoch(stamp: str) -> float:
        try:
            return calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
        except (ValueError, TypeError):
            return 0.0

    in_window = [r for r in runs if _epoch(r.timestamp) >= cutoff]
    failed = [r for r in in_window if r.verdict == "FAIL"]
    completed = [r for r in in_window if r.verdict in ("PASS", "WARN", "FAIL")]

    # One bucket per day, oldest first, so the client renders a real series
    # instead of inventing bar heights.
    buckets: Dict[str, Dict[str, int]] = {}
    for offset in range(days - 1, -1, -1):
        day = time.strftime("%Y-%m-%d", time.gmtime(time.time() - offset * 86_400))
        buckets[day] = {"runs": 0, "failed": 0}
    for record in in_window:
        day = str(record.timestamp)[:10]
        if day in buckets:
            buckets[day]["runs"] += 1
            if record.verdict == "FAIL":
                buckets[day]["failed"] += 1

    pass_rate = (
        round(100.0 * (len(completed) - len(failed)) / len(completed), 2)
        if completed
        else None
    )

    return {
        "window_days": days,
        "total_runs": len(in_window),
        "failed_runs": len(failed),
        "pass_rate": pass_rate,
        "measured": bool(in_window),
        "trend": [
            {"date": day, "runs": counts["runs"], "failed": counts["failed"]}
            for day, counts in buckets.items()
        ],
    }
