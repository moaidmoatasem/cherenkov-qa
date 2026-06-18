"""SOC 2 Type II report generator for CHERENKOV enterprise mode."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


class ControlCategory(str, Enum):
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class ControlStatus(str, Enum):
    OPERATIONAL = "operational"
    NOT_IMPLEMENTED = "not_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class Control:
    id: str
    name: str
    category: ControlCategory
    description: str
    status: ControlStatus = ControlStatus.NOT_IMPLEMENTED
    evidence: str = ""
    last_tested: float = 0.0
    owner: str = ""


# SOC 2 trust service criteria mapped to CHERENKOV controls
DEFAULT_CONTROLS: list[Control] = [
    Control(
        id="CC1.1",
        name="Access Control Policy",
        category=ControlCategory.SECURITY,
        description="Policies and procedures for logical access to systems and data.",
    ),
    Control(
        id="CC1.2",
        name="Authentication",
        category=ControlCategory.SECURITY,
        description="Authentication mechanisms for system access (SAML SSO).",
    ),
    Control(
        id="CC1.3",
        name="Authorization (RBAC)",
        category=ControlCategory.SECURITY,
        description="Role-based access control for least privilege.",
    ),
    Control(
        id="CC2.1",
        name="Audit Logging",
        category=ControlCategory.SECURITY,
        description="Comprehensive audit logging of all access and actions.",
    ),
    Control(
        id="CC3.1",
        name="Encryption at Rest",
        category=ControlCategory.CONFIDENTIALITY,
        description="Data encrypted at rest using industry-standard algorithms.",
    ),
    Control(
        id="CC3.2",
        name="Encryption in Transit",
        category=ControlCategory.CONFIDENTIALITY,
        description="All data in transit encrypted via TLS 1.2+.",
    ),
    Control(
        id="CC4.1",
        name="Incident Response",
        category=ControlCategory.SECURITY,
        description="Incident detection, reporting, and remediation procedures.",
    ),
    Control(
        id="CC5.1",
        name="Change Management",
        category=ControlCategory.PROCESSING_INTEGRITY,
        description="Controlled change management for system modifications.",
    ),
    Control(
        id="CC6.1",
        name="Data Retention",
        category=ControlCategory.PRIVACY,
        description="Data retention and disposal per GDPR/privacy requirements.",
    ),
    Control(
        id="CC6.2",
        name="Data Backup",
        category=ControlCategory.AVAILABILITY,
        description="Regular data backups with tested restoration procedures.",
    ),
    Control(
        id="CC7.1",
        name="Availability Monitoring",
        category=ControlCategory.AVAILABILITY,
        description="System availability monitoring and alerting.",
    ),
    Control(
        id="CC7.2",
        name="Disaster Recovery",
        category=ControlCategory.AVAILABILITY,
        description="Disaster recovery plan with defined RTO/RPO.",
    ),
    Control(
        id="CC8.1",
        name="Vulnerability Management",
        category=ControlCategory.SECURITY,
        description="Regular vulnerability scanning and patch management.",
    ),
    Control(
        id="CC9.1",
        name="Vendor Management",
        category=ControlCategory.SECURITY,
        description="Assessment and monitoring of third-party vendors.",
    ),
]


@dataclass
class SOC2Report:
    report_id: str
    organization: str
    report_date: str
    reporting_period: str
    controls: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    status: str = "draft"


class SOC2ReportGenerator:
    """SOC 2 Type II report generator.

    Assesses CHERENKOV's controls against SOC 2 trust service criteria
    and generates a structured report suitable for auditor review.
    """

    def __init__(self):
        self._controls: dict[str, Control] = {c.id: c for c in DEFAULT_CONTROLS}
        self._reports: dict[str, SOC2Report] = {}

    def get_controls(self) -> list[Control]:
        return list(self._controls.values())

    def update_control(
        self,
        control_id: str,
        status: ControlStatus | None = None,
        evidence: str | None = None,
        owner: str | None = None,
    ) -> bool:
        control = self._controls.get(control_id)
        if control is None:
            return False
        if status is not None:
            control.status = status
        if evidence is not None:
            control.evidence = evidence
        if owner is not None:
            control.owner = owner
        control.last_tested = time.time()
        return True

    def generate_report(self, organization: str) -> SOC2Report:
        import uuid

        report_id = f"soc2-{uuid.uuid4().hex[:8]}"
        report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        period_end = datetime.now(timezone.utc)
        m = period_end.month - 6
        y = period_end.year
        if m <= 0:
            m += 12
            y -= 1
        period_start = period_end.replace(year=y, month=m)
        reporting_period = f"{period_start.strftime('%Y-%m-%d')} to {report_date}"

        control_data = [
            {
                "id": c.id,
                "name": c.name,
                "category": c.category.value,
                "status": c.status.value,
                "evidence": c.evidence,
                "last_tested": (
                    datetime.fromtimestamp(c.last_tested, tz=timezone.utc).strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    )
                    if c.last_tested > 0
                    else "Not tested"
                ),
                "owner": c.owner,
            }
            for c in self._controls.values()
        ]

        total = len(control_data)
        operational = sum(1 for c in control_data if c["status"] == "operational")
        partial = sum(1 for c in control_data if c["status"] == "partially_implemented")
        not_impl = sum(1 for c in control_data if c["status"] == "not_implemented")
        coverage = operational / total if total > 0 else 0.0

        report = SOC2Report(
            report_id=report_id,
            organization=organization,
            report_date=report_date,
            reporting_period=reporting_period,
            controls=control_data,
            summary={
                "total_controls": total,
                "operational": operational,
                "partially_implemented": partial,
                "not_implemented": not_impl,
                "coverage_pct": round(coverage * 100, 1),
                "status": "compliant" if coverage >= 0.8 else "non_compliant",
            },
            status="draft",
        )
        self._reports[report_id] = report
        return report

    def get_report(self, report_id: str) -> SOC2Report | None:
        return self._reports.get(report_id)

    def list_reports(self) -> list[dict[str, str]]:
        return [
            {"report_id": r.report_id, "date": r.report_date, "status": r.status}
            for r in self._reports.values()
        ]

    def export_report(self, report_id: str, path: str) -> str:
        report = self._reports.get(report_id)
        if report is None:
            raise ValueError(f"Report not found: {report_id}")
        output_path = os.path.join(path, f"{report_id}.json")
        with open(output_path, "w") as f:
            json.dump(report.__dict__, f, indent=2, default=str)
        return output_path

    def get_compliance_summary(self) -> dict[str, Any]:
        by_category: dict[str, dict[str, int]] = {}
        for c in self._controls.values():
            cat = c.category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "operational": 0}
            by_category[cat]["total"] += 1
            if c.status == ControlStatus.OPERATIONAL:
                by_category[cat]["operational"] += 1
        return {
            category: {
                "total": v["total"],
                "operational": v["operational"],
                "coverage_pct": round(v["operational"] / v["total"] * 100, 1)
                if v["total"] > 0
                else 0.0,
            }
            for category, v in by_category.items()
        }


# Global singleton
_generator = SOC2ReportGenerator()


def get_soc2() -> SOC2ReportGenerator:
    return _generator
