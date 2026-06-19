"""Synthetic data runner — integrates with the pipeline."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cherenkov.synthetic.generator import (
    GenerationStrategy,
)


@dataclass
class SyntheticDataReport:
    """Report for a synthetic data generation run."""

    spec_path: str
    endpoint_count: int
    field_count: int
    generated_samples: int
    strategy: str
    duration_ms: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_path": self.spec_path,
            "endpoint_count": self.endpoint_count,
            "field_count": self.field_count,
            "generated_samples": self.generated_samples,
            "strategy": self.strategy,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


def generate_for_endpoints(
    spec_path: str,
    strategy: GenerationStrategy = GenerationStrategy.RANDOM,
    max_endpoints: int = 10,
    output_path: str | None = None,
) -> SyntheticDataReport:
    """Generate synthetic data for all endpoints in a spec.

    Args:
        spec_path: Path to OpenAPI spec.
        strategy: Generation strategy (RANDOM or LLM).
        max_endpoints: Maximum number of endpoints to process.
        output_path: Optional path to write results as JSON.

    Returns:
        A SyntheticDataReport with generation stats.
    """
    from cherenkov.synthetic.generator import generate_from_spec

    t0 = time.time()
    data = generate_from_spec(spec_path, strategy, max_endpoints)

    # Count fields
    field_count = 0
    generated_samples = 0
    for endpoint, samples in data.items():
        for sample_key, value in samples.items():
            generated_samples += 1
            if isinstance(value, dict):
                field_count += len(value)
            elif isinstance(value, list):
                field_count += len(value)

    report = SyntheticDataReport(
        spec_path=spec_path,
        endpoint_count=len(data),
        field_count=field_count,
        generated_samples=generated_samples,
        strategy=strategy.value,
        duration_ms=int((time.time() - t0) * 1000),
    )

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"report": report.to_dict(), "data": data}, indent=2))

    # Optional observability trace
    try:
        from cherenkov.observability.llm_tracer import trace_event
        trace_event(
            "synthetic-generation-complete",
            endpoints=report.endpoint_count,
            samples=report.generated_samples,
            fields=report.field_count,
            strategy=report.strategy,
            duration_ms=report.duration_ms,
        )
    except Exception:
        pass

    return report
