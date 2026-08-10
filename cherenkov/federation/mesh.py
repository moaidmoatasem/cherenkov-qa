"""Federation client for sharing knowledge mesh across CHERENKOV instances.

This is a lightweight stub implementation that uses HTTP GET/POST with a simple
Bearer token for mutual authentication. In production the client would be
expanded to support TLS verification, retries, and schema validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import urllib.request

_log = logging.getLogger(__name__)


class FederationClient:
    """Client to query a remote CHERENKOV knowledge mesh.

    Args:
        base_url: Base URL of the remote CHERENKOV instance, e.g.
            ``https://remote.cherenkov.dev``.
        token: Optional bearer token for authentication. If omitted, the
            client attempts unauthenticated access.
    """

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        _log.info("FederationClient initialized for %s", self.base_url)

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, data: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{path}"
        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method=method)
        for k, v in self._build_headers().items():
            req.add_header(k, v)
        _log.debug("Federation request %s %s", method, url)
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read().decode("utf-8")
            return json.loads(resp_data)

    # Public API -----------------------------------------------------------
    def ping(self) -> bool:
        """Simple health check – returns ``True`` if the remote responds.

        The remote is expected to expose ``/federation/ping`` returning a JSON
        ``{"status": "ok"}`` payload.
        """
        try:
            result = self._request("GET", "/federation/ping")
            return result.get("status") == "ok"
        except Exception as e:
            _log.error("Federation ping failed: %s", e)
            return False

    def query_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Query the remote mesh for a given *topic* (e.g. ``"api_schema"``).

        The remote endpoint ``/federation/query`` expects a JSON body
        ``{"topic": "..."}`` and returns a list of matching records.
        """
        try:
            response = self._request("POST", "/federation/query", {"topic": topic})
            return response.get("results", [])
        except Exception as e:
            _log.error("Federation query failed for %s: %s", topic, e)
            return []

    def push_local(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Push a local record to the remote mesh.

        The remote endpoint ``/federation/push`` receives ``{"topic": ..., "payload": ...}``.
        Returns ``True`` on success.
        """
        try:
            result = self._request("POST", "/federation/push", {"topic": topic, "payload": payload})
            return result.get("status") == "ok"
        except Exception as e:
            _log.error("Federation push failed: %s", e)
            return False
