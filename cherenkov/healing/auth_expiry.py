"""
CHERENKOV healing/auth_expiry.py — suggest-only auth-expiry failure healing module.
Authority: v3.1 + delta.
"""
from __future__ import annotations
import os

class AuthExpiryHealer:
    """Generates suggest-only setup steps to handle authentication token refresh issues without altering source files."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id

    def suggest_heal(self, scenario_id: str, endpoint: str) -> str:
        """Formulates a comprehensive, suggest-only CLI suggestion showing how to configure token refresh."""
        env_credentials = [
            "API_KEY", "CLIENT_SECRET", "ACCESS_TOKEN", "OAUTH_TOKEN", "BEARER_TOKEN"
        ]
        available_creds = [c for c in env_credentials if os.getenv(c)]
        
        suggestion = (
            "\n"
            "========================================================================\n"
            "⚠️  [HEALING SUGGESTION] - AUTHENTICATION EXPIRY / UNAUTHORIZED (401)\n"
            "========================================================================\n"
            f"Scenario '{scenario_id}' returned 401 Unauthorized against endpoint: {endpoint}\n\n"
            "To heal this honestly without manual code edits, configure your test client\n"
            "setup to automatically load credentials from environment variables.\n\n"
            "SUGGESTED ACTIONS:\n"
            "1. Export the correct authentication token in your shell environment:\n"
            "   export API_URL=\"http://localhost:8000\"\n"
            "   export BEARER_TOKEN=\"your_new_jwt_or_api_token\"\n\n"
            "2. Wrap your client invocation in a setup block that refreshes credentials:\n"
            "   ```typescript\n"
            "   // In stub/client.ts or your test setup:\n"
            "   export const client = createClient<paths>({\n"
            "     baseUrl: process.env.API_URL ?? 'http://localhost:8000',\n"
            "     headers: {\n"
            "       Authorization: `Bearer ${process.env.BEARER_TOKEN}`\n"
            "     }\n"
            "   });\n"
            "   ```\n"
        )
        if available_creds:
            suggestion += f"\nNote: Detected available credential environment variables: {available_creds}\n"
        else:
            suggestion += "\nNote: No active credential env variables (e.g. BEARER_TOKEN, API_KEY) were found on PATH.\n"
            
        suggestion += "========================================================================\n"
        return suggestion
