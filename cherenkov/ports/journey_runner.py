"""Port for starting and tracking journey runs.

Web-triggered runs are raw daemon threads tracked in a module-level dict, which
works for one process and only one process. Meanwhile the Kubernetes operator
reconciles ConformanceCheck resources into runs while bypassing the FastAPI app
entirely -- two ways to run the same thing, sharing nothing.

Naming the seam does not by itself make the engine distributed. It makes the
in-process executor one implementation rather than the only possibility, so the
operator (or a queue) can become a second one without the API layer changing.

Run state is durable regardless of implementation: the engine writes a
RunRecord at start and updates it on completion, so a run started by any runner
is addressable by id afterwards.
"""
from __future__ import annotations

from typing import Protocol


class JourneyRunner(Protocol):
    def start(self, journey_id: str, spec_path: str, run_id: str) -> str:
        """Begin a run and return its id. Returns as soon as it is scheduled."""
        ...

    def is_running(self, run_id: str) -> bool:
        """Whether this runner is currently executing the run.

        False from a runner that never had it -- ask the RunStore for the
        authoritative status, not the runner.
        """
        ...
