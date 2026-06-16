"""
cherenkov/truth/sources/traffic.py — E2-4: Traffic adapter (HAR / proxy replay).

Turn a captured traffic sample into observed-behaviour claims (enables D2/D5).
"""

from __future__ import annotations

import json
from pathlib import Path

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType
from cherenkov.truth.sources.interface import SourceAdapter


class TrafficSourceAdapter(SourceAdapter):
    """Source adapter for HAR (HTTP Archive) traffic captures.

    Imports HAR entries as observed-behaviour claims with provenance=traffic.
    """

    def discover_claims(self, source_uri: str) -> list[Claim]:
        uri_path = Path(source_uri)
        if not uri_path.exists():
            raise FileNotFoundError(f"HAR file not found: {source_uri}")

        raw = uri_path.read_text(encoding="utf-8")
        har = json.loads(raw)

        entries = har.get("log", {}).get("entries", [])
        if not entries:
            entries = har.get("entries", [])

        claims: list[Claim] = []
        resolved = uri_path.resolve()

        for i, entry in enumerate(entries):
            request = entry.get("request", {})
            response = entry.get("response", {})

            method = request.get("method", "GET").upper()
            url = request.get("url", "")
            status = response.get("status", 0)

            subject = f"{method} {url}"

            # Observed status claim
            claims.append(
                Claim(
                    id=f"traffic_{i}_status",
                    category="observed_status",
                    subject=subject,
                    value={
                        "status": status,
                        "statusText": response.get("statusText", ""),
                    },
                    provenance=Provenance(
                        source_type=ProvenanceType.TRAFFIC,
                        source_uri=str(resolved),
                        details={"type": "observed_http_status", "entry_index": i},
                    ),
                )
            )

            # Observed latency claim
            timings = entry.get("timings", {})
            if timings:
                total_ms = (
                    timings.get("send", 0)
                    + timings.get("wait", 0)
                    + timings.get("receive", 0)
                )
                claims.append(
                    Claim(
                        id=f"traffic_{i}_latency",
                        category="observed_latency",
                        subject=subject,
                        value={"total_ms": total_ms, "timings": timings},
                        provenance=Provenance(
                            source_type=ProvenanceType.TRAFFIC,
                            source_uri=str(resolved),
                            details={"type": "observed_latency", "entry_index": i},
                        ),
                    )
                )

            # Observed response headers claim
            headers = response.get("headers", [])
            if headers:
                header_dict = {h.get("name", ""): h.get("value", "") for h in headers}
                claims.append(
                    Claim(
                        id=f"traffic_{i}_headers",
                        category="observed_headers",
                        subject=subject,
                        value=header_dict,
                        provenance=Provenance(
                            source_type=ProvenanceType.TRAFFIC,
                            source_uri=str(resolved),
                            details={
                                "type": "observed_response_headers",
                                "entry_index": i,
                            },
                        ),
                    )
                )

            # Observed request body claim (for mutations)
            post_data = request.get("postData", {})
            if post_data.get("text"):
                claims.append(
                    Claim(
                        id=f"traffic_{i}_request_body",
                        category="observed_request_body",
                        subject=subject,
                        value={
                            "mimeType": post_data.get("mimeType", ""),
                            "text": post_data["text"],
                        },
                        provenance=Provenance(
                            source_type=ProvenanceType.TRAFFIC,
                            source_uri=str(resolved),
                            details={"type": "observed_request_body", "entry_index": i},
                        ),
                    )
                )

        return claims
