"""
cherenkov/verdict/traffic_capture.py — Real-traffic golden fixture capture.

Inspired by Keploy (API tests from real traffic) and Meticulous (session replay).

Intercepts every request/response pair that occurs during a proof run and
promotes passing ones (spec-conformant) to a golden fixture file in JSONL
format.  These fixtures can be replayed offline to catch regressions without
hitting the live API.

The capture runs as a lightweight wrapper around the WitnessAgent: it
instruments the HTTP calls by subclassing the agent and recording every
interaction.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import DivergenceHypothesis, ReproductionResult
from cherenkov.divergence.witness import WitnessAgent


@dataclass
class CapturedInteraction:
    """One recorded request/response pair from a live probe."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    method: str = "GET"
    url: str = ""
    request_body: dict | None = None
    response_status: int = 0
    response_body: Any = None
    response_headers: dict = field(default_factory=dict)
    latency_ms: int = 0
    spec_conformant: bool = True   # did this response match the spec?
    hypothesis_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_fixture(self) -> dict:
        return {
            "id": self.id,
            "method": self.method,
            "url": self.url,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_body": self.response_body,
            "response_headers": self.response_headers,
            "latency_ms": self.latency_ms,
            "spec_conformant": self.spec_conformant,
            "hypothesis_id": self.hypothesis_id,
            "captured_at": self.timestamp,
        }


@dataclass
class TrafficCaptureReport:
    interactions: list[CapturedInteraction] = field(default_factory=list)
    golden_count: int = 0          # spec_conformant interactions promoted
    fixture_path: str | None = None
    duration_ms: int = 0

    @property
    def total(self) -> int:
        return len(self.interactions)


class CapturingWitnessAgent(WitnessAgent):
    """
    WitnessAgent subclass that records every HTTP interaction it performs.

    All captures accumulate in `self.interactions`; call `dump_fixtures()`
    to write golden fixtures to disk.
    """

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        super().__init__(base_url=base_url, timeout=timeout)
        self.interactions: list[CapturedInteraction] = []

    def reproduce(self, hypothesis: DivergenceHypothesis) -> ReproductionResult:
        result = super().reproduce(hypothesis)
        if result.evidence:
            self._record(hypothesis, result)
        return result

    def dump_fixtures(self, output_path: str | Path) -> int:
        """Write golden (spec-conformant) fixtures to a JSONL file.

        Returns the number of fixtures written.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        golden = [i for i in self.interactions if i.spec_conformant]
        with path.open("w", encoding="utf-8") as fh:
            for interaction in golden:
                fh.write(json.dumps(interaction.to_fixture()) + "\n")
        return len(golden)

    # ── private ───────────────────────────────────────────────────────────

    def _record(
        self, hypothesis: DivergenceHypothesis, result: ReproductionResult
    ) -> None:
        ev = result.evidence
        if ev is None:
            return

        # Parse method + url from request_summary: "GET https://... → 200 (45ms)"
        parts = ev.request_summary.split()
        method = parts[0] if parts else "GET"
        url = parts[1] if len(parts) > 1 else ""

        # Parse latency from "(Xms)"
        latency_ms = 0
        for token in parts:
            if token.endswith("ms)") and token.startswith("("):
                with contextlib.suppress(ValueError):
                    latency_ms = int(token[1:-3])

        # Determine spec conformance: NOT reproduced → response matched spec
        spec_conformant = not result.reproduced

        self.interactions.append(
            CapturedInteraction(
                method=method,
                url=url,
                response_body=ev.response_actual,
                latency_ms=latency_ms,
                spec_conformant=spec_conformant,
                hypothesis_id=hypothesis.id,
            )
        )


class TrafficCapture:
    """
    Orchestrates a proof run using a CapturingWitnessAgent, then promotes
    spec-conformant interactions to golden fixtures.

    Usage::

        capture = TrafficCapture(base_url="https://petstore3.swagger.io/api/v3")
        report = capture.run(hypotheses, fixture_dir=".cherenkov/fixtures")
        print(f"{report.golden_count} golden fixtures written to {report.fixture_path}")
    """

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.agent = CapturingWitnessAgent(base_url=base_url, timeout=timeout)

    def run(
        self,
        hypotheses: list[DivergenceHypothesis],
        fixture_dir: str | Path = ".cherenkov/fixtures",
    ) -> TrafficCaptureReport:
        """Reproduce all hypotheses and capture every interaction."""
        t0 = time.monotonic()

        for h in hypotheses:
            self.agent.reproduce(h)

        fixture_path: str | None = None
        golden_count = 0
        if self.agent.interactions:
            path = Path(fixture_dir) / f"capture_{int(time.time())}.jsonl"
            golden_count = self.agent.dump_fixtures(path)
            fixture_path = str(path)

        duration_ms = int((time.monotonic() - t0) * 1000)
        return TrafficCaptureReport(
            interactions=list(self.agent.interactions),
            golden_count=golden_count,
            fixture_path=fixture_path,
            duration_ms=duration_ms,
        )

    def replay(self, fixture_path: str | Path) -> list[dict]:
        """Load and return all interactions from a golden fixture file."""
        path = Path(fixture_path)
        if not path.exists():
            return []
        fixtures: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        fixtures.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return fixtures


class RecordingProxy:
    """Forwarding HTTP proxy that records what a test suite actually receives.

    `CapturingWitnessAgent` above records CHERENKOV's *own* probe traffic. This
    records *someone else's* suite: point their `API_URL` at this proxy, run
    the suite, and every request is forwarded to the real target while the
    response is captured.

    This is the record half of record-then-perturb, the only sound basis for a
    baseline-free audit. A spec constrains types, not instance values, so
    mutating a schema-sampled body makes an honest suite fail its own
    conforming control and voids every verdict — see
    `docs/evidence/e0.5e_oracle_discrimination.md`. Feed `recorded_base()`
    into `synthesize_mutant_battery(..., base=...)` instead.

    Use as a context manager:

        with RecordingProxy(port=9100, target="https://api.example.com") as rec:
            runner.execute_test(scenario_id=..., test_code=..., api_url=rec.url)
        base = rec.recorded_base("/orders/42")
    """

    def __init__(self, port: int, target: str, timeout: float = 30.0) -> None:
        self.port = port
        self.target = target.rstrip("/")
        self.timeout = timeout
        self.interactions: list[CapturedInteraction] = []
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> RecordingProxy:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def start(self) -> None:
        proxy = self

        class _Handler(BaseHTTPRequestHandler):
            def _forward(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                started = time.monotonic()

                req = urllib.request.Request(
                    proxy.target + self.path,
                    data=raw or None,
                    method=self.command,
                    headers={
                        k: v
                        for k, v in self.headers.items()
                        # Host must reflect the real target; hop-by-hop headers
                        # and the original length are recomputed downstream.
                        if k.lower() not in ("host", "content-length", "connection")
                    },
                )
                try:
                    with urllib.request.urlopen(req, timeout=proxy.timeout) as resp:
                        status, body, headers = resp.status, resp.read(), dict(resp.headers)
                except urllib.error.HTTPError as exc:
                    # A 4xx/5xx is a real answer worth recording, not a failure.
                    status, body, headers = exc.code, exc.read(), dict(exc.headers or {})
                except Exception as exc:
                    status, body, headers = 502, json.dumps({"error": str(exc)}).encode(), {}

                proxy._record(self.command, self.path, raw, status, body, headers, started)

                self.send_response(status)
                self.send_header(
                    "Content-Type", headers.get("Content-Type", "application/json")
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_: object) -> None:
                pass

            do_GET = _forward  # noqa: N815
            do_POST = _forward  # noqa: N815
            do_PUT = _forward  # noqa: N815
            do_DELETE = _forward  # noqa: N815
            do_PATCH = _forward  # noqa: N815

        self._server = HTTPServer(("127.0.0.1", self.port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name=f"recording-proxy-{self.port}",
        )
        self._thread.start()

    def _record(
        self,
        method: str,
        path: str,
        raw_request: bytes,
        status: int,
        body: bytes,
        headers: dict,
        started: float,
    ) -> None:
        self.interactions.append(
            CapturedInteraction(
                method=method,
                url=path,
                request_body=_maybe_json(raw_request),
                response_status=status,
                response_body=_maybe_json(body),
                response_headers=headers,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
            self._thread = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def recorded_base(self, path: str) -> tuple[int, Any] | None:
        """The last recorded (status, body) for `path`, ready for the battery.

        Last rather than first: a suite that mutates state should be perturbed
        against the response its assertions were written against most recently.
        """
        for interaction in reversed(self.interactions):
            if interaction.url == path:
                return interaction.response_status, interaction.response_body
        return None

    def replay_map(self) -> dict[str, tuple[int, Any]]:
        """Every recorded path as a `BrokenImplServer` response map."""
        return {
            i.url: (i.response_status, i.response_body)
            for i in self.interactions
        }


def _maybe_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")
