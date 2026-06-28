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

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

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
                try:
                    latency_ms = int(token[1:-3])
                except ValueError:
                    pass

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
        t0 = time.time()

        for h in hypotheses:
            self.agent.reproduce(h)

        fixture_path: str | None = None
        golden_count = 0
        if self.agent.interactions:
            path = Path(fixture_dir) / f"capture_{int(time.time())}.jsonl"
            golden_count = self.agent.dump_fixtures(path)
            fixture_path = str(path)

        duration_ms = int((time.time() - t0) * 1000)
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
