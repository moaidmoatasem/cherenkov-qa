"""Routine Template: Daily Health Check."""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def run(project_id: str | None = None) -> None:
    """Run a comprehensive health check on the CHERENKOV system or specific project."""
    _log.info(f"Running daily health check for project={project_id}")
    # In a full implementation, this would trigger the actual health check logic
    # similar to `cherenkov doctor`
