"""Auth helpers shared across API sub-routers.

Delegates to cherenkov.security.auth for constant-time implementation.
"""
from __future__ import annotations

from cherenkov.security.auth import verify_api_key, verify_write_access

__all__ = ["verify_api_key", "verify_write_access"]
