from __future__ import annotations

import re

from cherenkov.adversarial.core import (
    DetectionResult,
    Severity,
    ThreatCategory,
)


_EXFIL_PATTERNS = [
    (r"fetch\s*\(\s*['\"]https?://(?!localhost|127\.0\.0\.1)", "External URL fetch detected"),
    (r"XMLHttpRequest", "XMLHttpRequest usage detected"),
    (r"navigator\.sendBeacon", "sendBeacon data exfiltration detected"),
    (r"new\s+Image\s*\(\s*['\"]https?://", "Image beacon exfiltration detected"),
    (r"document\.createElement\s*\(\s*['\"]script['\"]", "Dynamic script injection detected"),
]

_CMD_INJECTION_PATTERNS = [
    (r"eval\s*\(", "eval() usage detected"),
    (r"Function\s*\(", "Function constructor detected"),
    (r"child_process", "child_process module detected"),
    (r"require\s*\(\s*['\"]child_process['\"]", "child_process require detected"),
    (r"exec\s*\(\s*['\"]", "exec() with string argument detected"),
    (r"execSync\s*\(", "execSync usage detected"),
    (r"spawn\s*\(", "spawn usage detected"),
    (r"process\.env", "process.env access detected"),
]

_TAUTOLOGICAL_PATTERNS = [
    (r"expect\s*\(\s*true\s*\)", "Tautological assertion: expect(true)"),
    (r"expect\s*\(\s*false\s*\)\.toBe\s*\(\s*false\s*\)", "Tautological assertion: expect(false).toBe(false)"),
    (r"expect\s*\(\s*1\s*\)\.toBe\s*\(\s*1\s*\)", "Tautological assertion: expect(1).toBe(1)"),
    (r"catch\s*\([^)]*\)\s*\{\s*\}", "Empty catch block — swallows failures silently"),
    (r"expect\s*\(\s*res\s*\)\.toBeTruthy\s*\(\s*\)", "Weak assertion: toTruthy on entire response object"),
    (r"expect\s*\(\s*response\s*\)\.toBeTruthy\s*\(\s*\)", "Weak assertion: toTruthy on entire response object"),
    (r"expect\s*\(\s*res\s*\)\.toBeDefined\s*\(\s*\)", "Vacuous assertion: response is always defined"),
    (r"expect\s*\(\s*response\s*\)\.toBeDefined\s*\(\s*\)", "Vacuous assertion: response is always defined"),
    (r"expect\s*\(\s*res\.status\s*\)\.toBeGreaterThan\s*\(\s*0\s*\)", "Vacuous assertion: any HTTP status > 0"),
    (r"expect\s*\(\s*res\.status\s*\)\.toBeLessThan\s*\(\s*600\s*\)", "Vacuous assertion: any HTTP status < 600"),
    (r"\.toBeInstanceOf\s*\(\s*Object\s*\)", "Weak assertion: toBeInstanceOf(Object) — any object passes"),
]

_WEAK_BODY_ASSERTION_PATTERNS = [
    (r"expect\s*\(\s*body\s*\)\.toBeTruthy\s*\(\s*\)", "Weak body assertion: toTruthy on body"),
    (r"expect\s*\(\s*data\s*\)\.toBeTruthy\s*\(\s*\)", "Weak body assertion: toTruthy on data"),
    (r"expect\s*\(\s*json\s*\)\.toBeTruthy\s*\(\s*\)", "Weak body assertion: toTruthy on json"),
    (r"expect\s*\(\s*body\s*\)\.toBeDefined\s*\(\s*\)", "Weak body assertion: toBeDefined on body"),
    (r"expect\s*\(\s*data\s*\)\.toBeDefined\s*\(\s*\)", "Weak body assertion: toBeDefined on data"),
    (r"expect\s*\(typeof\s+\w+\)\.toBe\s*\(\s*['\"]object['\"]\s*\)", "Weak type assertion: typeof === object"),
    (r"Object\.keys\s*\(\s*\w+\s*\)\.length\s*>=?\s*0", "Vacuous length check: always >= 0"),
]

_SPEC_MANIPULATION_PATTERNS = [
    (r"\/admin\/delete", "Suspicious admin delete endpoint"),
    (r"\/admin\/drop", "Suspicious admin drop endpoint"),
    (r"DROP\s+TABLE", "SQL DROP TABLE detected"),
    (r"rm\s+-rf", "Destructive rm -rf command detected"),
]

_PROMPT_INJECTION_MARKERS = [
    (r"<\|im_start\|>", "Prompt injection marker: im_start"),
    (r"<\|im_end\|>", "Prompt injection marker: im_end"),
    (r"<\|system\|>", "Prompt injection marker: system role"),
    (r"###\s*System:", "Prompt injection marker: system directive"),
    (r"---\s*INSTRUCT", "Prompt injection marker: instruction override"),
]


def _scan_patterns(
    test_code: str,
    patterns: list[tuple[str, str]],
    category: ThreatCategory,
    severity: Severity,
) -> list[DetectionResult]:
    results = []
    for pattern, detail in patterns:
        match = re.search(pattern, test_code, re.IGNORECASE)
        if match:
            snippet = test_code[max(0, match.start() - 20):match.end() + 20]
            results.append(
                DetectionResult(
                    payload_id=f"{category.value}-{pattern[:20]}",
                    category=category,
                    detected=True,
                    severity=severity,
                    detail=detail,
                    test_code_snippet=snippet.strip(),
                )
            )
    return results


def scan_test_code(test_code: str) -> list[DetectionResult]:
    results: list[DetectionResult] = []
    results.extend(_scan_patterns(test_code, _EXFIL_PATTERNS, ThreatCategory.DATA_EXFILTRATION, Severity.CRITICAL))
    results.extend(_scan_patterns(test_code, _CMD_INJECTION_PATTERNS, ThreatCategory.COMMAND_INJECTION, Severity.HIGH))
    results.extend(_scan_patterns(test_code, _TAUTOLOGICAL_PATTERNS, ThreatCategory.TAUTOLOGICAL_TEST, Severity.MEDIUM))
    results.extend(_scan_patterns(test_code, _WEAK_BODY_ASSERTION_PATTERNS, ThreatCategory.TAUTOLOGICAL_TEST, Severity.LOW))
    results.extend(_scan_patterns(test_code, _SPEC_MANIPULATION_PATTERNS, ThreatCategory.SPEC_MANIPULATION, Severity.HIGH))
    results.extend(_scan_patterns(test_code, _PROMPT_INJECTION_MARKERS, ThreatCategory.PROMPT_INJECTION, Severity.CRITICAL))
    return results


def has_meaningful_body_assertion(test_code: str) -> bool:
    """Return True if the test code contains at least one assertion that actually
    constrains the response body (not just status code or vacuous checks).

    Used by E1.2 meaningful-assertion gate to reject status-code-only suites.
    """
    meaningful_patterns = [
        # Direct body/data/json/result object field access
        r"expect\s*\(\s*(?:body|data|json|result)\.",
        # response.body.field or response.data.field — not response.status
        r"expect\s*\(\s*(?:res|response)\.(?:body|data|json)\b",
        # Deep equality
        r"\.toEqual\s*\(",
        # Property existence + value
        r"\.toHaveProperty\s*\(",
        # Array/string containment
        r"\.toContain\s*\(",
        # Non-zero length check
        r"\.toHaveLength\s*\(\s*[1-9]",
        # Partial object match
        r"\.toMatchObject\s*\(",
        # Bracket-access assertions on body/data
        r"expect\s*\(\s*(?:body|data|json|result)\[",
        # Named field access like pets[0].name or pet.id
        r"expect\s*\(\s*\w+\[0\]\.",
    ]
    return any(re.search(p, test_code) for p in meaningful_patterns)


def scan_batch(test_codes: dict[str, str]) -> dict[str, list[DetectionResult]]:
    return {name: scan_test_code(code) for name, code in test_codes.items()}
