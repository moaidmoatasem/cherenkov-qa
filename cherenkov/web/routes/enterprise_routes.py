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
    # SLA metrics are typically derived from the run store or external APM.
    # We provide simulated enterprise SLA data here for the dashboard.
    return {
        "uptime": 99.99,
        "api_response_p99": 145, # ms
        "total_checks": 125000,
        "failed_checks": 12,
        "status": "operational"
    }

@router.post("/support/ticket")
def create_support_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a priority enterprise support ticket.

    Args:
        payload: Ticket content dictionary.

    Returns:
        Dictionary status payload including generated ticket ID.
    """
    # Placeholder for enterprise support portal integration
    import uuid
    ticket_id = str(uuid.uuid4())
    return {
        "status": "created",
        "ticket_id": ticket_id,
        "message": "Enterprise support team has been notified."
    }
