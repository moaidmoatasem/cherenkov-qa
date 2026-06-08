"""
CHERENKOV healing/contract_drift.py -- suggest-only contract-drift diffing and suggestion module.
Authority: v3.1 + delta.
"""
from __future__ import annotations

class ContractDriftHealer:
    """Provides detailed suggest-only reports for contract shape drift with loud visual regression warnings."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id

    def suggest_heal(
        self,
        scenario_id: str,
        endpoint: str,
        method: str,
        missing_fields: list[str],
        added_fields: list[str]
    ) -> dict:
        """Constructs the suggest-only CLI contract drift warning and correction assertion block.

        Returns a structured dict with a 'suggestion' key containing the human-readable text.
        """
        lines = [
            "",
            "========================================================================  ",
            "  [HEALING SUGGESTION] - CONTRACT DRIFT DETECTED",
            "========================================================================  ",
            f"Endpoint: {method} {endpoint} (Scenario '{scenario_id}')",
        ]

        # 1. Flag RED regression on field removal
        if missing_fields:
            lines.extend([
                "",
                " [RED REGRESSION] - CRITICAL: Fields were REMOVED from the API response!",
                f"  Missing fields: {missing_fields}",
                "  Impact: Unhealed clients relying on these properties will CRASH at runtime.",
            ])

        # 2. Flag YELLOW review warning on field addition
        if added_fields:
            lines.extend([
                "",
                " [YELLOW WARNING] - REVIEW NEEDED: New fields were ADDED to the API response!",
                f"  Added fields: {added_fields}",
                "  [LOUD ALERT] is this intended? Please confirm if the API contract expanded.",
            ])

        # 3. Suggest updated assertion blocks
        lines.extend([
            "",
            "SUGGESTED CLIENT ASSERTION UPDATE:",
            "Update your Playwright test assertion to reflect the current contract shape honestly:",
            "```typescript",
            f"// In stub/generated_tests/{scenario_id}.spec.ts:",
        ])
        for am in added_fields:
            lines.append(f"expect(data).toHaveProperty('{am}'); // New property")
        for rm in missing_fields:
            lines.append(f"// expect(data).toHaveProperty('{rm}'); // REMOVED from contract")
        lines.extend([
            "```",
            "========================================================================  ",
        ])

        return {
            "healed": False,
            "healer": "ContractDriftHealer",
            "scenario_id": scenario_id,
            "endpoint": endpoint,
            "method": method,
            "missing_fields": missing_fields,
            "added_fields": added_fields,
            "suggestion": "\n".join(lines),
        }
