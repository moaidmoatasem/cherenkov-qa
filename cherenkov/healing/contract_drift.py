"""
CHERENKOV healing/contract_drift.py — suggest-only contract-drift diffing and suggestion module.
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
    ) -> str:
        """Constructs the suggest-only CLI contract drift warning and correction assertion block."""
        suggestion = (
            "\n"
            "========================================================================\n"
            "⚠️  [HEALING SUGGESTION] - CONTRACT DRIFT DETECTED\n"
            "========================================================================\n"
            f"Endpoint: {method} {endpoint} (Scenario '{scenario_id}')\n"
        )
        
        # 1. Flag RED regression on field removal
        if missing_fields:
            suggestion += (
                "\n"
                "🛑 [RED REGRESSION] - CRITICAL: Fields were REMOVED from the API response!\n"
                f"  Missing fields: {missing_fields}\n"
                "  Impact: Unhealed clients relying on these properties will CRASH at runtime.\n"
            )
            
        # 2. Flag YELLOW review warning on field addition
        if added_fields:
            suggestion += (
                "\n"
                "⚠️ [YELLOW WARNING] - REVIEW NEEDED: New fields were ADDED to the API response!\n"
                f"  Added fields: {added_fields}\n"
                "  [LOUD ALERT] is this intended? Please confirm if the API contract expanded.\n"
            )

        # 3. Suggest updated assertion blocks
        suggestion += (
            "\n"
            "SUGGESTED CLIENT ASSERTION UPDATE:\n"
            "Update your Playwright test assertion to reflect the current contract shape honestly:\n"
            "```typescript\n"
            f"// In stub/generated_tests/{scenario_id}.spec.ts:\n"
        )
        
        # Build TypeScript assertions code suggestion
        for am in added_fields:
            suggestion += f"expect(data).toHaveProperty('{am}'); // New property\n"
        for rm in missing_fields:
            suggestion += f"// expect(data).toHaveProperty('{rm}'); // REMOVED from contract\n"
            
        suggestion += (
            "```\n"
            "========================================================================\n"
        )
        return suggestion
