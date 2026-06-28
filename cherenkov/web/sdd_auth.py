"""Auth helpers shared across API sub-routers.

Delegates to cherenkov.security.auth for constant-time implementation.
"""

from cherenkov.security.auth import verify_api_key, verify_write_access  # noqa: F401
