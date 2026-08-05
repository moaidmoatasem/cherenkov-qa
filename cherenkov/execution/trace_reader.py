"""
CHERENKOV execution/trace_reader.py — programmatic Playwright trace.zip parser.
"""

from __future__ import annotations

import base64
import json
import os
import zipfile

from cherenkov.core.errors import get_logger


class TraceReader:
    """Programmatically extracts HTTP status codes and response bodies from native Playwright trace.zip archives."""

    def __init__(self, run_id: str | None = None):
        self.log = get_logger("TRACE_READER", run_id)

    def extract_http_response(
        self, trace_zip_path: str, target_path: str, method: str
    ) -> dict | None:
        """Parses trace.zip programmatically to find the HTTP response status and body shape for the matched call."""
        if not trace_zip_path or not os.path.exists(trace_zip_path):
            self.log.warning("trace.zip file does not exist", path=trace_zip_path)
            return None

        self.log.info(
            "parsing trace.zip file",
            path=trace_zip_path,
            target_path=target_path,
            method=method,
        )

        try:
            with zipfile.ZipFile(trace_zip_path, "r") as z:
                # Playwright trace.zip typically contains 'trace.network' or similar network log files
                network_files = [
                    f for f in z.namelist() if "network" in f or f.endswith(".network")
                ]

                for net_file in network_files:
                    with z.open(net_file) as f:
                        for line in f:
                            try:
                                event = json.loads(line.decode("utf-8"))
                                event_type = event.get("type", "")

                                # Look for network responses/events
                                is_net_event = (
                                    event_type == "resource"
                                    or event_type == "resource-snapshot"
                                    or "response" in event
                                    or "snapshot" in event
                                )

                                if is_net_event:
                                    # Playwright trace formats: could be in params, snapshot or root event
                                    params = event.get("params", event)
                                    if "snapshot" in event:
                                        params = event["snapshot"]

                                    request = params.get("request") or {}
                                    response = params.get("response") or {}
                                    if not isinstance(request, dict):
                                        request = {}
                                    if not isinstance(response, dict):
                                        response = {}

                                    req_method = request.get(
                                        "method", params.get("method", "")
                                    )
                                    req_url = request.get("url", params.get("url", ""))

                                    # Check if this matches our target path and method
                                    if (
                                        req_method.upper() == method.upper()
                                        and target_path in req_url
                                    ):
                                        status = response.get(
                                            "status", params.get("status", 0)
                                        )

                                        # 1. Locate request body postData sent
                                        req_body_raw = ""
                                        post_data = request.get("postData")
                                        if isinstance(post_data, dict):
                                            sha1 = post_data.get("_sha1")
                                            if sha1:
                                                try:
                                                    with z.open(
                                                        f"resources/{sha1}"
                                                    ) as res_f:
                                                        req_body_raw = (
                                                            res_f.read().decode("utf-8")
                                                        )
                                                except Exception as _exc:
                                                    self.log.warning("HAR zip resource not found for request body", error=str(_exc))
                                            if not req_body_raw:
                                                req_body_raw = post_data.get("text", "")

                                        if not req_body_raw:
                                            req_body_raw = request.get(
                                                "postDataText", ""
                                            )
                                        if not req_body_raw:
                                            req_body_raw = params.get("postData", "")

                                        # 2. Locate response body shape
                                        body_content = ""

                                        # Try content._sha1 first if present in response
                                        content = response.get("content")
                                        if isinstance(content, dict):
                                            sha1 = content.get("_sha1")
                                            if sha1:
                                                try:
                                                    with z.open(
                                                        f"resources/{sha1}"
                                                    ) as res_f:
                                                        body_content = (
                                                            res_f.read().decode("utf-8")
                                                        )
                                                except Exception as _exc:
                                                    self.log.warning("HAR zip resource not found for response body", error=str(_exc))

                                        if not body_content:
                                            body_data = response.get(
                                                "body", params.get("responseBody", "")
                                            )
                                            if body_data and isinstance(body_data, str):
                                                    try:
                                                        body_content = base64.b64decode(
                                                            body_data
                                                        ).decode("utf-8")
                                                    except (ValueError, UnicodeDecodeError) as _exc:
                                                        self.log.debug(
                                                            "response body is not base64/utf-8; using raw value",
                                                            error=str(_exc),
                                                        )
                                                        body_content = body_data

                                        # Parse body shape
                                        body_keys = []
                                        if body_content:
                                            try:
                                                body_json = json.loads(body_content)
                                                if isinstance(body_json, dict):
                                                    body_keys = list(body_json)
                                            except json.JSONDecodeError as _exc:
                                                self.log.debug(
                                                    "response body is not JSON; body_keys left empty",
                                                    error=str(_exc),
                                                )

                                        self.log.info(
                                            "extracted http call from trace",
                                            method=req_method,
                                            url=req_url,
                                            status=status,
                                            body_keys=body_keys,
                                        )
                                        return {
                                            "status": status,
                                            "body_keys": body_keys,
                                            "body_raw": body_content,
                                            "request_body_raw": req_body_raw,
                                        }
                            except Exception as _exc:
                                self.log.warning(
                                    "skipping unparseable trace entry",
                                    error=f"{type(_exc).__name__}: {_exc}",
                                )
                                continue
        except Exception as e:
            self.log.error("failed programmatically parsing trace.zip", error=str(e))

        return None
