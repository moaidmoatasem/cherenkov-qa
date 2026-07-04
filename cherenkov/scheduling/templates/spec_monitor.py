"""Routine Template: OpenAPI Spec Monitor."""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def run(spec_url: str) -> None:
    """Monitor an OpenAPI spec URL for changes and trigger drift detection."""
    _log.info("Monitoring OpenAPI spec at %s", spec_url)
    # Integration with cherenkov.spec_guardian would happen here
