"""
CHERENKOV compliance/mena_scanner.py — MENA Cyber Security Framework Compliance Auditor.
"""

from __future__ import annotations

import os
import json
import time
import requests

from cherenkov.core.errors import get_logger


class MENAComplianceScanner:
    """Audits API endpoints and contracts against SAMA CCSF and Egypt FinCSF financial cybersecurity standards."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("MENA_SCANNER", run_id)
        self.report_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../.cherenkov")
        )
        self.report_path = os.path.join(self.report_dir, "mena_compliance_report.json")

    def run_compliance_audit(self, target_url: str, spec_path: str) -> dict:
        """Executes a dynamic endpoint header audit and static OpenAPI contract validation for SAMA/FinCSF."""
        self.log.info(
            "starting MENA cyber security framework compliance audit",
            target_url=target_url,
        )

        audit_results = {
            "tls_enforced": False,
            "hsts_present": False,
            "clickjacking_protection": False,
            "mime_sniffing_protection": False,
            "bearer_auth_defined": False,
            "errors": [],
        }

        # 1. Dynamic Endpoint Audit (Active check of security headers)
        try:
            resp = requests.get(target_url, timeout=5)
            headers = resp.headers

            # TLS check (Localhost accepted as secure baseline, otherwise must be HTTPS)
            audit_results["tls_enforced"] = (
                target_url.startswith("https")
                or "127.0.0.1" in target_url
                or "localhost" in target_url
            )

            # Security Header Checks
            audit_results["hsts_present"] = "Strict-Transport-Security" in headers
            audit_results["clickjacking_protection"] = (
                "X-Frame-Options" in headers or "Frame-Options" in headers
            )
            audit_results["mime_sniffing_protection"] = (
                headers.get("X-Content-Type-Options") == "nosniff"
            )

        except Exception as e:
            self.log.warning(
                "failed to actively query target headers, performing static contract-only audit",
                error=str(e),
            )
            audit_results["errors"].append(f"Target connection failed: {e}")

        # 2. Static OpenAPI Contract Audit (Authentication structures)
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)

            components = spec.get("components", {})
            security_schemes = components.get("securitySchemes", {})

            # Check if secure Bearer token authentication is specified
            for scheme_name, scheme in security_schemes.items():
                if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
                    audit_results["bearer_auth_defined"] = True
                    break
        except Exception as e:
            self.log.error(
                "failed to parse OpenAPI spec for compliance check", error=str(e)
            )
            audit_results["errors"].append(f"Spec parsing failed: {e}")

        # 3. Formulate CCSF & FinCSF Compliance Matrices
        score = 0
        if audit_results["tls_enforced"]:
            score += 20
        if audit_results["hsts_present"]:
            score += 20
        if audit_results["clickjacking_protection"]:
            score += 20
        if audit_results["mime_sniffing_protection"]:
            score += 20
        if audit_results["bearer_auth_defined"]:
            score += 20

        # Mapping assertions directly to regional monetary clauses
        sama_mapping = {
            "SAMA CCSF Domain 3.1 (Cyber Security Governance)": {
                "status": "COMPLIANT"
                if audit_results["bearer_auth_defined"]
                else "NON-COMPLIANT",
                "clause": "3.1.2 Access Control & Structured Authentication Policies",
                "remediation": "Define robust HTTP Bearer token credentials within the securitySchemes of the OpenAPI contract.",
            },
            "SAMA CCSF Domain 3.2 (Cyber Security Operations)": {
                "status": "COMPLIANT"
                if (audit_results["tls_enforced"] and audit_results["hsts_present"])
                else "NON-COMPLIANT",
                "clause": "3.2.3 Data-in-Transit Protection and Secure Communication Protocols",
                "remediation": "Enforce TLS v1.3 secure connection routing and emit HSTS (Strict-Transport-Security) headers from backend gateway.",
            },
            "SAMA CCSF Domain 3.3 (Cyber Security Architecture)": {
                "status": "COMPLIANT"
                if (
                    audit_results["clickjacking_protection"]
                    and audit_results["mime_sniffing_protection"]
                )
                else "NON-COMPLIANT",
                "clause": "3.3.1 Application Hardening and Frame/MIME Validation",
                "remediation": "Configure web response headers to emit X-Frame-Options: DENY and X-Content-Type-Options: nosniff.",
            },
        }

        egypt_fincsf_mapping = {
            "CBE FinCSF Section 4.2 (Secure Software Development Lifecycle)": {
                "status": "COMPLIANT"
                if audit_results["bearer_auth_defined"]
                else "NON-COMPLIANT",
                "remediation": "Ensure all API interactions authenticate users through cryptographically signed access tokens.",
            },
            "CBE FinCSF Section 4.5 (Boundary Protection & Defensive Hardening)": {
                "status": "COMPLIANT" if (score >= 80) else "NON-COMPLIANT",
                "remediation": "Ensure standard security headers are consistently injected to mitigate clickjacking and MIME injection attempts.",
            },
        }

        report = {
            "timestamp": int(time.time()),
            "target_url": target_url,
            "spec_path": spec_path,
            "overall_compliance_score": score,
            "audit_results": audit_results,
            "framework_mappings": {
                "SAMA_CCSF": sama_mapping,
                "EGYPT_FinCSF": egypt_fincsf_mapping,
            },
        }

        # Write audit report to disk
        os.makedirs(self.report_dir, exist_ok=True)
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        self.log.info(
            "compliance audit report completed successfully",
            score=score,
            path=self.report_path,
        )
        return report
