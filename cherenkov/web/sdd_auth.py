"""Auth helpers shared across API sub-routers.

Delegates to cherenkov.security.auth for constant-time implementation.
"""

from cherenkov.security.auth import verify_write_access, verify_api_key  # noqa: F401
