"""
CHERENKOV reporting/session_report.py — Context-rich session report builder.

Aggregates findings from the entire validation / exploration session into a
single, self-contained deliverable: HTTP verdicts, visual diffs, VLM
classifications, JS errors, and explorer anomalies.

Inspired by the "context-rich issue reports" model described in the
vibe-testing literature — every finding carries a full AI-generated
explanation, embedded screenshot (base64), trace path, and actionable
suggestions so a developer can reproduce and fix without re-running.

Design invariants:
  - Suggest-only (D7): never modifies test files or auto-applies fixes.
  - All evidence is optional — missing artefacts degrade gracefully.
  - to_dict() strips base64 screenshots for JSON log safety; to_rich_dict()
    includes them for HTML/UI rendering.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from cherenkov.core.errors import get_logger


# ── data models ──────────────────────────────────────────────────────────────


@dataclass
class SessionFinding:
    kind: str  # "http_verdict" | "visual_anomaly" | "js_error" | "explorer"
    severity: str  # "low" | "medium" | "high" | "critical"
    title: str
    detail: str
    url: str
    evidence: dict = field(default_factory=dict)
    ai_explanation: str = ""
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self, include_screenshots: bool = False) -> dict:
        ev = dict(self.evidence)
        if not include_screenshots:
            ev.pop("screenshot_b64", None)
        return {
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "url": self.url,
            "evidence": ev,
            "ai_explanation": self.ai_explanation,
            "suggestions": self.suggestions,
        }


@dataclass
class SessionReport:
    session_id: str
    target_url: str
    generated_at: float
    findings: list[SessionFinding]
    summary: dict
    vlm_classifications: list[dict]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "target_url": self.target_url,
            "generated_at": self.generated_at,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "vlm_classifications": self.vlm_classifications,
            "metadata": self.metadata,
        }

    def to_rich_dict(self) -> dict:
        """Includes base64 screenshots for UI rendering."""
        d = self.to_dict()
        d["findings"] = [f.to_dict(include_screenshots=True) for f in self.findings]
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def write(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())


# ── builder ───────────────────────────────────────────────────────────────────


class SessionReportBuilder:
    """Fluent builder — accumulate findings from multiple sources, then call build()."""

    def __init__(self, target_url: str, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.target_url = target_url
        self._findings: list[SessionFinding] = []
        self._vlm: list[dict] = []
        self._log = get_logger("session-report", self.session_id)

    # ── http conformance ──────────────────────────────────────────────────

    def add_http_verdict(
        self,
        url: str,
        method: str,
        expected_status: int,
        actual_status: int,
        response_body: str = "",
        trace_path: str = "",
    ) -> "SessionReportBuilder":
        if actual_status == expected_status:
            return self
        severity = "critical" if actual_status >= 500 else "high"
        self._findings.append(
            SessionFinding(
                kind="http_verdict",
                severity=severity,
                title=f"{method} {url} — status mismatch",
                detail=f"Spec declares {expected_status}, live server returned {actual_status}",
                url=url,
                evidence={
                    "trace_path": trace_path,
                    "response_excerpt": response_body[:300] if response_body else "",
                },
                ai_explanation=(
                    f"The OpenAPI spec declares HTTP {expected_status} for {method} {url} "
                    f"but the live server returned {actual_status}. "
                    f"This is a spec-code divergence (D1_SPEC_CODE). "
                    f"{'A 5xx response indicates a server crash or unhandled exception.' if actual_status >= 500 else ''}"
                ),
                suggestions=[
                    f"Inspect the handler for {method} {url}",
                    "Compare the route implementation against the OpenAPI operation object",
                    "Run `cherenkov validate` for the full conformance report",
                    "Check application logs for errors triggered by this request",
                ],
            )
        )
        return self

    # ── visual regression ─────────────────────────────────────────────────

    def add_visual_finding(
        self,
        url: str,
        vlm_kind: str,
        vlm_detail: str,
        vlm_confidence: float,
        screenshot_path: str = "",
        baseline_path: str = "",
    ) -> "SessionReportBuilder":
        screenshot_b64 = _encode_image(screenshot_path)
        severity_map = {
            "anomaly": "high",
            "harmless_shift": "low",
            "redesign": "medium",
            "unknown": "low",
        }
        severity = severity_map.get(vlm_kind, "low")
        self._findings.append(
            SessionFinding(
                kind="visual_anomaly",
                severity=severity,
                title=f"Visual change — {vlm_kind} (confidence {vlm_confidence:.0%})",
                detail=vlm_detail,
                url=url,
                evidence={
                    "screenshot_b64": screenshot_b64,
                    "baseline_path": baseline_path,
                    "vlm_kind": vlm_kind,
                    "vlm_confidence": vlm_confidence,
                },
                ai_explanation=vlm_detail,
                suggestions=_visual_suggestions(vlm_kind),
            )
        )
        self._vlm.append(
            {
                "url": url,
                "kind": vlm_kind,
                "confidence": vlm_confidence,
                "detail": vlm_detail,
            }
        )
        return self

    # ── JS / browser errors ───────────────────────────────────────────────

    def add_js_error(self, url: str, error_text: str) -> "SessionReportBuilder":
        self._findings.append(
            SessionFinding(
                kind="js_error",
                severity="high",
                title="JavaScript runtime error",
                detail=error_text,
                url=url,
                ai_explanation=(
                    "A JavaScript runtime error was caught in the browser console. "
                    "This indicates a frontend bug that may silently break user interactions "
                    "without a visible crash."
                ),
                suggestions=[
                    "Open browser DevTools and reproduce manually",
                    "Check the source file and line number in the stack trace",
                    "Ensure all imported modules are bundled and available",
                ],
            )
        )
        return self

    # ── explorer findings ─────────────────────────────────────────────────

    def add_explorer_finding(self, finding: Any) -> "SessionReportBuilder":
        """Accept a cherenkov.core.contracts.ExplorerFinding object."""
        sev_raw = str(getattr(finding, "severity", "medium")).lower().split(".")[-1]
        severity = (
            sev_raw if sev_raw in ("low", "medium", "high", "critical") else "medium"
        )
        kind_val = (
            finding.kind.value if hasattr(finding.kind, "value") else str(finding.kind)
        )
        self._findings.append(
            SessionFinding(
                kind="explorer",
                severity=severity,
                title=f"{kind_val} — {finding.url}",
                detail=finding.detail,
                url=finding.url,
                evidence={
                    "status": finding.status,
                    "latency_ms": finding.latency_ms,
                    "evidence": finding.evidence,
                    "method": finding.method,
                },
                ai_explanation=finding.detail,
                suggestions=[
                    f"Verify {finding.method} {finding.url} manually",
                    "Check server logs for the time of this probe",
                ],
            )
        )
        return self

    # ── visual report integration ─────────────────────────────────────────

    def add_visual_report(self, report: Any) -> "SessionReportBuilder":
        """Accept a cherenkov.core.contracts.VisualReport and ingest its gates."""
        for gate in getattr(report, "gates", []):
            if gate.gate == "vlm_semantic":
                continue
            if not gate.passed:
                vlm_gate = next(
                    (
                        g
                        for g in getattr(report, "gates", [])
                        if g.gate == "vlm_semantic"
                    ),
                    None,
                )
                kind = "unknown"
                detail = "Visual pixel diff detected"
                conf = 0.0
                if vlm_gate:
                    kind = "anomaly" if not vlm_gate.passed else "harmless_shift"
                self.add_visual_finding(
                    url=getattr(report, "scenario_id", ""),
                    vlm_kind=kind,
                    vlm_detail=detail,
                    vlm_confidence=conf,
                    screenshot_path=gate.actual_path,
                    baseline_path=gate.baseline_path,
                )
        return self

    # ── build ─────────────────────────────────────────────────────────────

    def build(self) -> SessionReport:
        severity_counts = Counter(f.severity for f in self._findings)
        return SessionReport(
            session_id=self.session_id,
            target_url=self.target_url,
            generated_at=time.time(),
            findings=list(self._findings),
            summary={
                "total": len(self._findings),
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
            },
            vlm_classifications=list(self._vlm),
            metadata={
                "session_id": self.session_id,
                "target_url": self.target_url,
                "builder": "SessionReportBuilder",
            },
        )


# ── helpers ───────────────────────────────────────────────────────────────────


def _encode_image(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode()
    except Exception:
        return ""


def _visual_suggestions(kind: str) -> list[str]:
    if kind == "anomaly":
        return [
            "Inspect the UI for broken CSS or missing assets",
            "Check recent style or markup changes",
            "Run visual regression with --update-snapshots only after confirming the change",
        ]
    if kind == "redesign":
        return [
            "Confirm the visual change was intentional with the designer",
            "Update the baseline: `cherenkov validate --update-visual`",
        ]
    if kind == "harmless_shift":
        return [
            "Consider raising the pixel diff threshold in playwright.config.ts",
            "Add `--ignore-antialiasing` to the snapshot options",
        ]
    return ["Review the screenshot manually before updating the baseline"]
