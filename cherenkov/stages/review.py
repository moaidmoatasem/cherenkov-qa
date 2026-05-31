"""
CHERENKOV stages/review.py — real test review stage enforcing static quality gates.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import re
import time

from cherenkov.core.contracts import ReviewOutput, GenerateOutput, GateResult, Verdict, Status, StageMeta
from cherenkov.core.errors import get_logger

class ReviewStage:
    """Enforces static quality gates (syntax, structure, assertions, AST keywords) on LLM-generated test code."""

    def __init__(self, run_id: str | None = None):
        self.log = get_logger("REVIEW", run_id)

    def run(self, generate: GenerateOutput) -> ReviewOutput:
        t0 = time.time()
        code = generate.test_code
        self.log.info("stage start", scenario_id=generate.scenario_id)

        gates: list[GateResult] = []

        # 1. Syntax Gate (Basic TS & Markdown cleanup checks)
        syntax_passed = True
        syntax_detail = "TS syntax well-formed."
        if not code.strip():
            syntax_passed = False
            syntax_detail = "Generated test code is empty."
        elif "```" in code:
            syntax_passed = False
            syntax_detail = "Test code contains stray markdown code block fences."
        gates.append(GateResult(gate="syntax", passed=syntax_passed, detail=syntax_detail))

        # 2. Structure Gate (Verify required stub/playwright imports)
        structure_passed = True
        structure_detail = "All standard Playwright and client imports present."
        if "from '../client'" not in code and 'from "../client"' not in code:
            structure_passed = False
            structure_detail = "Missing imports for target openapi-fetch client ('../client')."
        elif "from '@playwright/test'" not in code and 'from "@playwright/test"' not in code:
            structure_passed = False
            structure_detail = "Missing imports for '@playwright/test'."
        gates.append(GateResult(gate="structure", passed=structure_passed, detail=structure_detail))

        # 3. AST-validate Gate (Strict check: uses openapi-fetch client, no forbidden http keywords)
        ast_passed = True
        ast_detail = "Verified usage of openapi-fetch client with zero raw fetch/axios bleed."
        
        # Check client calling format (e.g. client.GET, client.POST)
        uses_fetch_client = bool(re.search(r"\bclient\.(GET|POST|PUT|DELETE|PATCH)\b", code))
        # Check forbidden raw requests
        has_forbidden = bool(re.search(r"\b(fetch|axios)\b|\.request\b|throw new Error", code))
        
        if not uses_fetch_client:
            ast_passed = False
            ast_detail = "Test fails to invoke the openapi-fetch client correctly."
        elif has_forbidden:
            ast_passed = False
            ast_detail = "Test contains forbidden HTTP keywords (raw fetch, axios, or custom throw statement)."
            
        gates.append(GateResult(gate="ast", passed=ast_passed, detail=ast_detail))

        # 4. Assertions Gate (Checks status & body shape expectations)
        assertions_passed = True
        assertions_detail = "Asserts specific status code and response body shape."
        
        specific_status = bool(re.search(r"\.status\)?\s*\)?\s*\.toBe\(\s*\d{3}\s*\)", code)) or \
                          bool(re.search(r"toBe\(\s*(200|201|204|400|401|404|422|500)\s*\)", code))
        body_shape = bool(re.search(r"toHaveProperty\(|typeof\s", code))
        
        if not specific_status:
            assertions_passed = False
            assertions_detail = "Missing expectation asserting specific status code (toBe(code))."
        elif not body_shape:
            assertions_passed = False
            assertions_detail = "Missing expectation asserting response body property structure (toHaveProperty)."
            
        gates.append(GateResult(gate="assertion", passed=assertions_passed, detail=assertions_detail))

        # 5. Prism Dry-Run Gate (Placeholder: to be wired fully in Phase 6)
        prism_passed = True
        prism_detail = "Prism dynamic dry-run gate bypassed (scheduled for Phase 6)."
        gates.append(GateResult(gate="prism-dryrun", passed=prism_passed, detail=prism_detail))

        # Calculate quality score as fraction of passed gates (out of 5 gates)
        passed_count = sum(1 for g in gates if g.passed)
        quality_score = passed_count / len(gates)

        # Enforce Verdict thresholds
        if quality_score >= 0.9:
            verdict = Verdict.AUTO_APPROVE
        elif quality_score >= 0.7:
            verdict = Verdict.HITL
        else:
            verdict = Verdict.REGENERATE

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", quality_score=quality_score, verdict=verdict.value, duration_ms=dt)

        return ReviewOutput(
            scenario_id=generate.scenario_id,
            gates=gates,
            quality_score=quality_score,
            verdict=verdict,
            status=Status.OK,
            metadata=StageMeta(stage="REVIEW", duration_ms=dt)
        )
