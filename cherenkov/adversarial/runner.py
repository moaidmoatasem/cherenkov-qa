from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cherenkov.adversarial.core import (
    AdversarialReport,
    DetectionResult,
    Severity,
    ThreatCategory,
)
from cherenkov.adversarial.detector import scan_test_code
from cherenkov.adversarial.garak_adapter import is_garak_available, run_garak
from cherenkov.adversarial.injector import get_payloads


def run_adversarial_tests(
    test_codes: dict[str, str],
    spec_path: str | None = None,
    model: str = "static-analysis",
) -> AdversarialReport:
    results: list[DetectionResult] = []

    for name, code in test_codes.items():
        detections = scan_test_code(code)
        for d in detections:
            d.payload_id = f"{name}:{d.payload_id}"
        if not detections:
            results.append(
                DetectionResult(
                    payload_id=f"{name}:clean",
                    category=ThreatCategory.PROMPT_INJECTION,
                    detected=False,
                    severity=Severity.LOW,
                    detail="No adversarial patterns detected",
                )
            )
        else:
            results.extend(detections)

    garak_available = is_garak_available()
    garak_findings: list[dict[str, Any]] = []
    if garak_available and spec_path:
        garak_result = run_garak(spec_path)
        garak_findings = garak_result.get("findings", [])

    return AdversarialReport(
        results=results,
        model=model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        garak_available=garak_available,
        garak_findings=garak_findings,
    )


def print_report(report: AdversarialReport) -> None:
    d = report.to_dict()
    print(f"\n{'='*60}")
    print(f"  CHERENKOV ADVERSARIAL REPORT")
    print(f"{'='*60}")
    print(f"  Model:         {report.model}")
    print(f"  Pass rate:     {d['pass_rate']:.1%}")
    print(f"  Total checks:  {d['total_payloads']}")
    print(f"  Detected:      {d['detected']}")
    print(f"  Critical:      {d['critical']}")
    print(f"  Garak:         {'available' if report.garak_available else 'not installed'}")
    print(f"{'-'*60}")

    criticals = report.critical_findings()
    if criticals:
        print(f"\n  CRITICAL FINDINGS:")
        for f in criticals:
            print(f"    [{f.severity.value.upper()}] {f.category.value}: {f.detail}")
            if f.test_code_snippet:
                print(f"      -> {f.test_code_snippet[:80]}")

    if report.garak_findings:
        print(f"\n  GARAK FINDINGS ({len(report.garak_findings)}):")
        for gf in report.garak_findings[:5]:
            status = "PASS" if gf.get("passed") else "FAIL"
            print(f"    [{status}] {gf.get('probe', '?')}: {gf.get('prompt', '')[:60]}")

    print(f"{'='*60}\n")


def save_report(report: AdversarialReport, output_path: str = ".cherenkov/adversarial_report.json") -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2))
    return str(path)
