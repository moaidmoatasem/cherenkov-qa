"""
CHERENKOV healing/auth_expiry.py -- suggest-only auth-expiry failure healing module.
Authority: v3.1 + delta.
"""

from __future__ import annotations
import os


class AuthExpiryHealer:
    """Generates suggest-only setup steps to handle authentication token refresh issues without altering source files."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id

    def suggest_heal(self, scenario_id: str, endpoint: str) -> dict:
        """Formulates a suggest-only CLI suggestion showing how to configure token refresh.

        Returns a structured dict with a 'suggestion' key containing the human-readable text.
        """
        env_credentials = [
            "API_KEY",
            "CLIENT_SECRET",
            "ACCESS_TOKEN",
            "OAUTH_TOKEN",
            "BEARER_TOKEN",
        ]
        available_creds = [c for c in env_credentials if os.getenv(c)]

        lines = [
            "",
            "========================================================================  ",
            "  [HEALING SUGGESTION] - AUTHENTICATION EXPIRY / UNAUTHORIZED (401)",
            "========================================================================  ",
            f"Scenario '{scenario_id}' returned 401 Unauthorized against endpoint: {endpoint}",
            "",
            "To heal this honestly without manual code edits, configure your test client",
            "setup to automatically load credentials from environment variables.",
            "",
            "SUGGESTED ACTIONS:",
            "1. Export the correct authentication token in your shell environment:",
            '   export API_URL="http://localhost:8000"',
            '   export BEARER_TOKEN="your_new_jwt_or_api_token"',
            "",
            "2. Wrap your client invocation in a setup block that refreshes credentials:",
            "   ```typescript",
            "   // In stub/client.ts or your test setup:",
            "   export const client = createClient<paths>({",
            "     baseUrl: process.env.API_URL ?? 'http://localhost:8000',",
            "     headers: {",
            "       Authorization: `Bearer ${process.env.BEARER_TOKEN}`",
            "     }",
            "   });",
            "   ```",
        ]
        if available_creds:
            lines.append(
                f"\nNote: Detected available credential environment variables: {available_creds}\n"
            )
        else:
            lines.append(
                "\nNote: No active credential env variables (e.g. BEARER_TOKEN, API_KEY) were found on PATH.\n"
            )

        lines.append(
            "========================================================================  "
        )
        return {
            "healed": False,
            "healer": "AuthExpiryHealer",
            "scenario_id": scenario_id,
            "endpoint": endpoint,
            "suggestion": "\n".join(lines),
        }
