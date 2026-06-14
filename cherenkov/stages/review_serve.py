"""
cherenkov/stages/review_serve.py   [DEPRECATED]

This module is superseded by `cherenkov.web.api` (FastAPI) launched via
`cherenkov review --port 8000`. All functionality (HITL queue listing,
approve/reject, static UI serving) is available on the FastAPI server.

Keeping this file alive for backwards compatibility only — it prints a
deprecation warning and delegates to `cherenkov review`.
"""

from __future__ import annotations

import logging
import warnings

logger = logging.getLogger(__name__)

DEPRECATION_MSG = (
    "[DEPRECATED] review_serve.py is superseded by `cherenkov.web.api` (FastAPI). "
    "Use `cherenkov review --port 8000` instead. "
    "This module will be removed in a future release."
)


def run_review_server() -> int:
    """Execute `cherenkov review` — now delegates to the FastAPI server."""
    warnings.warn(DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    logger.warning(DEPRECATION_MSG)
    print(DEPRECATION_MSG)
    # Delegate to the canonical FastAPI server
    import uvicorn
    from cherenkov.web.api import app

    print("\nCHERENKOV review dashboard starting on http://0.0.0.0:8000")
    print("Hit Ctrl+C to stop.\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    return 0
