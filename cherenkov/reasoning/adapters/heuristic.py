"""
HeuristicReasoner — deterministic L0 reasoning backend (ADR-007 §3).

Zero I/O, zero LLM. Pattern-based analysis that is honest about its
depth: it finds structural gaps (missing error responses, untestable
requirement wording), not semantic ones. It is the always-available
fallback and the unit-test substrate; LLM adapters add insight on top.
"""
from __future__ import annotations

import re

from cherenkov.reasoning.domain.models import (
    AnalysisResult,
    Artifact,
    ArtifactKind,
    Depth,
    FindingCategory,
    Requirement,
    ReviewFinding,
    RiskItem,
    TestCaseDesign,
    priority_from_score,
)

_REQ_PATTERN = re.compile(r"^.*\b(shall|must|should|will|needs? to)\b.*$", re.IGNORECASE | re.MULTILINE)
_VAGUE_WORDS = re.compile(
    r"\b(fast|quick|easy|simple|user-friendly|appropriate|reasonable|etc\.?|some|various|as needed)\b",
    re.IGNORECASE,
)
_MUTATING = {"post", "put", "patch", "delete"}
_HIGH_IMPACT_TOPICS = re.compile(r"\b(auth|login|password|payment|billing|delete|data loss|pii|security)\b", re.IGNORECASE)

_DEPTH_CAPS = {Depth.SHALLOW: 10, Depth.MEDIUM: 30, Depth.DEEP: 60, Depth.EXHAUSTIVE: 10_000}


class HeuristicReasoner:
    """Deterministic ReasoningBackend implementation."""

    # ── analyze ───────────────────────────────────────────────────────

    def analyze(self, artifact: Artifact, depth: Depth) -> AnalysisResult:
        if artifact.kind == ArtifactKind.OPENAPI_SPEC:
            return self._analyze_spec(artifact, depth)
        return self._analyze_text(artifact, depth)

    def _analyze_spec(self, artifact: Artifact, depth: Depth) -> AnalysisResult:
        cap = _DEPTH_CAPS[depth]
        info = artifact.parsed.get("info", {})
        intents = [info.get("title", artifact.name)]
        requirements: list[Requirement] = []
        ambiguities: list[str] = []
        count = 0
        for path, ops in sorted(artifact.parsed.get("paths", {}).items()):
            for method, op in sorted(ops.items()):
                if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                    continue
                count += 1
                if len(requirements) >= cap:
                    continue
                ref = f"{method.upper()} {path}"
                for status in sorted((op or {}).get("responses", {})):
                    requirements.append(
                        Requirement(
                            id=f"REQ-{len(requirements) + 1:03d}",
                            text=f"{ref} responds {status} per spec",
                            source_ref=ref,
                        )
                    )
                if not (op or {}).get("description") and not (op or {}).get("summary"):
                    ambiguities.append(f"{ref} has no description or summary")
        return AnalysisResult(
            intents=intents, requirements=requirements, ambiguities=ambiguities, surface_size=count
        )

    def _analyze_text(self, artifact: Artifact, depth: Depth) -> AnalysisResult:
        cap = _DEPTH_CAPS[depth]
        requirements: list[Requirement] = []
        ambiguities: list[str] = []
        for match in _REQ_PATTERN.finditer(artifact.content):
            if len(requirements) >= cap:
                break
            sentence = match.group(0).strip().lstrip("-* ")
            requirements.append(
                Requirement(
                    id=f"REQ-{len(requirements) + 1:03d}",
                    text=sentence,
                    source_ref=artifact.name,
                    testable=not _VAGUE_WORDS.search(sentence),
                )
            )
        for req in requirements:
            if not req.testable:
                ambiguities.append(f"{req.id} uses vague wording: {req.text[:80]}")
        return AnalysisResult(
            intents=[artifact.name],
            requirements=requirements,
            ambiguities=ambiguities,
            surface_size=len(requirements),
        )

    # ── review ────────────────────────────────────────────────────────

    def review(
        self, artifact: Artifact, analysis: AnalysisResult, depth: Depth
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        if artifact.kind == ArtifactKind.OPENAPI_SPEC:
            for path, ops in sorted(artifact.parsed.get("paths", {}).items()):
                for method, op in sorted(ops.items()):
                    if method.lower() not in _MUTATING and method.lower() != "get":
                        continue
                    responses = (op or {}).get("responses", {})
                    ref = f"{method.upper()} {path}"
                    if not any(str(s).startswith("4") for s in responses):
                        findings.append(
                            ReviewFinding(
                                category=FindingCategory.GAP,
                                severity="medium",
                                description=f"{ref} documents no 4xx error response",
                                recommendation="Document expected client-error behavior so it can be tested",
                                source_ref=ref,
                            )
                        )
                    if method.lower() in _MUTATING and not (op or {}).get("security") \
                            and not artifact.parsed.get("security"):
                        findings.append(
                            ReviewFinding(
                                category=FindingCategory.RISK,
                                severity="high",
                                description=f"{ref} mutates state but declares no security requirement",
                                recommendation="Declare a security scheme or confirm the endpoint is intentionally open",
                                source_ref=ref,
                            )
                        )
        for req in analysis.requirements:
            if not req.testable:
                findings.append(
                    ReviewFinding(
                        category=FindingCategory.UNTESTABLE,
                        severity="medium",
                        description=f"{req.id} is not objectively verifiable: {req.text[:100]}",
                        recommendation="Restate with a measurable acceptance criterion",
                        source_ref=req.source_ref,
                    )
                )
        return findings

    # ── risk assessment ───────────────────────────────────────────────

    def assess_risks(
        self, artifact: Artifact, analysis: AnalysisResult, depth: Depth
    ) -> list[RiskItem]:
        risks: list[RiskItem] = []
        for req in analysis.requirements:
            impact = 4 if _HIGH_IMPACT_TOPICS.search(req.text) else 2
            mutating = any(m in req.source_ref.lower() for m in ("post", "put", "patch", "delete"))
            likelihood = 3 if not req.testable else 2
            if mutating:
                impact = min(impact + 1, 5)
                likelihood = max(likelihood, 3)  # state-changing surfaces fail more often
            risks.append(
                RiskItem(
                    id=f"RISK-{len(risks) + 1:03d}",
                    description=f"Failure of: {req.text[:100]}",
                    likelihood=likelihood,
                    impact=impact,
                    requirement_refs=[req.id],
                )
            )
        risks.sort(key=lambda r: r.score, reverse=True)
        return risks

    # ── case design ───────────────────────────────────────────────────

    def design_cases(
        self,
        artifact: Artifact,
        analysis: AnalysisResult,
        risks: list[RiskItem],
        depth: Depth,
    ) -> list[TestCaseDesign]:
        cap = _DEPTH_CAPS[depth]
        risk_by_req: dict[str, RiskItem] = {}
        for risk in risks:
            for ref in risk.requirement_refs:
                risk_by_req.setdefault(ref, risk)

        cases: list[TestCaseDesign] = []
        for req in analysis.requirements:
            if len(cases) >= cap:
                break
            risk = risk_by_req.get(req.id)
            case = TestCaseDesign(
                id=f"TC-{len(cases) + 1:03d}",
                title=f"Verify: {req.text[:80]}",
                requirement_ref=req.id,
                risk_refs=[risk.id] if risk else [],
                rationale=(
                    f"Covers {req.id}"
                    + (f"; mitigates {risk.id} (score {risk.score})" if risk else "")
                ),
                expected=req.text,
                priority=priority_from_score(risk.score) if risk else "P3",
            )
            if artifact.kind == ArtifactKind.OPENAPI_SPEC:
                self._bind_spec_fields(case, req)
            cases.append(case)
        return cases

    @staticmethod
    def _bind_spec_fields(case: TestCaseDesign, req: Requirement) -> None:
        """Bind endpoint/method/status SELECTED from the spec-derived requirement.

        The requirement text is 'METHOD /path responds NNN per spec' — both
        halves came from the spec, never from the reasoner's imagination.
        """
        match = re.match(r"(\w+) (\S+) responds (\d{3}) per spec", req.text)
        if not match:
            return
        case.method, case.endpoint = match.group(1), match.group(2)
        case.expected_status = int(match.group(3))
        case.case_type = "happy_path" if case.expected_status < 400 else "error_branch"
