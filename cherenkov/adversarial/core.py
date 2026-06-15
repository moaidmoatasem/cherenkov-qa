from __future__ import annotations

import dataclasses
import enum
from typing import Any


class ThreatCategory(enum.Enum):
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    COMMAND_INJECTION = "command_injection"
    SPEC_MANIPULATION = "spec_manipulation"
    TAUTOLOGICAL_TEST = "tautological_test"


class Severity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclasses.dataclass
class InjectionPayload:
    id: str
    category: ThreatCategory
    payload: str
    description: str
    severity: Severity = Severity.MEDIUM


@dataclasses.dataclass
class DetectionResult:
    payload_id: str
    category: ThreatCategory
    detected: bool
    severity: Severity
    detail: str
    test_code_snippet: str = ""


@dataclasses.dataclass
class AdversarialReport:
    results: list[DetectionResult]
    model: str
    timestamp: str
    garak_available: bool = False
    garak_findings: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def pass_rate(self) -> float:
        if not self.results:
            return 1.0
        return sum(1 for r in self.results if not r.detected) / len(self.results)

    def critical_findings(self) -> list[DetectionResult]:
        return [r for r in self.results if r.detected and r.severity in (Severity.HIGH, Severity.CRITICAL)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate": self.pass_rate(),
            "total_payloads": len(self.results),
            "detected": sum(1 for r in self.results if r.detected),
            "passed": sum(1 for r in self.results if not r.detected),
            "critical": len(self.critical_findings()),
            "garak_available": self.garak_available,
            "garak_findings": self.garak_findings,
            "results": [
                {
                    "payload_id": r.payload_id,
                    "category": r.category.value,
                    "detected": r.detected,
                    "severity": r.severity.value,
                    "detail": r.detail,
                }
                for r in self.results
            ],
            "model": self.model,
            "timestamp": self.timestamp,
        }
