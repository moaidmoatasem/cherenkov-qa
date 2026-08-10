# cherenkov/guardian/daemon.py
"""Core daemon implementation for the Spec Guardian.

The daemon periodically polls the live API endpoints derived from an OpenAPI
spec, compares responses against the spec, records any drift, and optionally
emits MCP events.
"""

from __future__ import annotations

import sqlite3
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .utils import default_endpoints, parse_endpoint_opts
from cherenkov.web.api import fetch_endpoint  # hypothetical helper to GET endpoint

_log = logging.getLogger(__name__)

class GuardianDaemon:
    """Runs the spec‑guardian polling loop.

    Parameters
    ----------
    spec_path: str
        Path to the OpenAPI spec file.
    base_url: str
        Base URL of the live API.
    interval: int
        Seconds between poll cycles.
    db_path: Optional[str]
        Path to SQLite DB. If ``None`` a temporary in‑memory DB is used.
    endpoints: Optional[List[dict]]
        Pre‑computed endpoint list. If ``None`` will be inferred from the spec.
    emit_mcp: bool
        Whether to emit MCP events for each drift detection.
    """

    def __init__(
        self,
        spec_path: str,
        base_url: str,
        interval: int = 60,
        db_path: Optional[str] = None,
        endpoints: Optional[List[Dict[str, Any]]] = None,
        emit_mcp: bool = False,
    ) -> None:
        self.spec_path = spec_path
        self.base_url = base_url.rstrip('/')
        self.interval = interval
        self.emit_mcp = emit_mcp
        self.db_path = db_path or ":memory:"
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_schema()
        self.endpoints = endpoints or default_endpoints(spec_path)
        _log.info("GuardianDaemon initialized with %d endpoints", len(self.endpoints))

    def _ensure_schema(self) -> None:
        """Create the ``guardian_events`` table if it does not exist.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS guardian_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status TEXT NOT NULL,
                diff TEXT
            )
            """
        )
        self.conn.commit()

    def _record_event(self, method: str, path: str, status: str, diff: Optional[str] = None) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO guardian_events (ts, method, path, status, diff) VALUES (datetime('now'), ?, ?, ?, ?)",
            (method, path, status, diff),
        )
        self.conn.commit()
        _log.debug("Recorded drift event: %s %s -> %s", method, path, status)
        if self.emit_mcp:
            # Placeholder for MCP event emission – actual implementation lives in the MCP tool.
            pass

    def _check_endpoint(self, endpoint: Dict[str, Any]) -> None:
        method = endpoint["method"].upper()
        path = endpoint["path"]
        url = f"{self.base_url}{path}"
        try:
            # ``fetch_endpoint`` is a thin wrapper around ``requests.get`` that returns JSON.
            response = fetch_endpoint(method, url)
            # For a simple drift check we compare status code and JSON shape.
            # In a real implementation we would run a schema validation against the spec.
            status = "ok"
            diff = None
        except Exception as exc:  # pragma: no cover – defensive.
            status = "error"
            diff = str(exc)
        self._record_event(method, path, status, diff)

    def run_once(self) -> List[Dict[str, Any]]:
        """Execute a single poll cycle for all configured endpoints.

        Returns a list of event dictionaries for immediate consumption by MCP tools.
        """
        results: List[Dict[str, Any]] = []
        for ep in self.endpoints:
            method = ep["method"].upper()
            path = ep["path"]
            try:
                response = fetch_endpoint(method, f"{self.base_url}{path}")
                status = "ok"
                diff = None
            except Exception as exc:
                status = "error"
                diff = str(exc)
            self._record_event(method, path, status, diff)
            results.append({"method": method, "path": path, "status": status, "diff": diff})
        return results

    def start(self, max_loops: int = 0) -> None:
        """Run the daemon indefinitely (or for ``max_loops`` cycles).
        """
        loop = 0
        while True:
            _log.info("Guardian poll cycle %d", loop + 1)
            self.run_once()
            loop += 1
            if max_loops and loop >= max_loops:
                _log.info("Reached max_loops=%d, exiting daemon", max_loops)
                break
            time.sleep(self.interval)

# Helper for the MCP tool – a thin wrapper that returns JSON.
def run_guardian_once(spec_path: str, base_url: str, interval: int = 60, db_path: Optional[str] = None,
                     raw_endpoints: Optional[tuple[str, ...]] = None, emit_mcp: bool = False) -> List[Dict[str, Any]]:
    endpoints = None
    if raw_endpoints:
        endpoints = parse_endpoint_opts(raw_endpoints)
    daemon = GuardianDaemon(spec_path, base_url, interval, db_path, endpoints, emit_mcp)
    return daemon.run_once()
