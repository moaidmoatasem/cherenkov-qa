from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OCRSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class OCRFinding:
    file: str
    line: int = 0
    column: int = 0
    severity: OCRSeverity = OCRSeverity.INFO
    rule: str = ""
    message: str = ""
    suggestion: str = ""


@dataclass
class OCRProvider:
    name: str
    base_url: str = ""
    model: str = ""
    protocol: str = "anthropic"
    auth_header: str = "x-api-key"
    auth_token: str = ""


@dataclass
class OCRReviewOutput:
    passed: bool = True
    findings: list[OCRFinding] = field(default_factory=list)
    score_deduction: float = 0.0
    agent_summary: str = ""
    llm_model: str = ""
    llm_provider: str = ""
    tokens_used: int = 0
    duration_ms: int = 0
    error: str = ""

    def __post_init__(self):
        if self.findings and self.score_deduction == 0.0:
            critical_count = sum(1 for f in self.findings if f.severity == OCRSeverity.CRITICAL)
            high_count = sum(1 for f in self.findings if f.severity == OCRSeverity.HIGH)
            medium_count = sum(1 for f in self.findings if f.severity == OCRSeverity.MEDIUM)
            self.score_deduction = (critical_count * 0.15) + (high_count * 0.10) + (medium_count * 0.05)
