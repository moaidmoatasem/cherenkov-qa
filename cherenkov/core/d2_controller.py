from __future__ import annotations

from cherenkov.core.contracts import IngestOutput, Scenario


class D2FeedbackController:
    """Tracks per-endpoint and per-case-type replan state for the D2 Planner Feedback loop."""

    def __init__(self, last_ingest: IngestOutput | None = None):
        self.last_ingest = last_ingest
        self.replans_per_endpoint: dict[str, int] = {}
        self.fails_per_case_type: dict[tuple, int] = {}

    def reset(self, last_ingest: IngestOutput | None = None) -> None:
        self.replans_per_endpoint.clear()
        self.fails_per_case_type.clear()
        if last_ingest is not None:
            self.last_ingest = last_ingest

    def should_retry(self, endpoint: str, case_type: str) -> bool:
        """Check if the D2 circuit breaker allows another replan attempt."""
        if self.fails_per_case_type.get((endpoint, case_type), 0) >= 2:
            return False
        return self.replans_per_endpoint.get(endpoint, 0) < 3

    def record_failure(self, endpoint: str, case_type: str) -> None:
        self.replans_per_endpoint[endpoint] = self.replans_per_endpoint.get(endpoint, 0) + 1
        self.fails_per_case_type[(endpoint, case_type)] = self.fails_per_case_type.get((endpoint, case_type), 0) + 1

    def get_next_mutation(
        self, current_scenario: Scenario, case_type: str
    ) -> Scenario | None:
        """Select the next untried mutation from the endpoint's mutation menu."""
        if not self.last_ingest:
            return None
        endpoint = current_scenario.endpoint
        endpoint_slice = None
        for ep in self.last_ingest.endpoints:
            if ep.path == endpoint and ep.method.upper() == current_scenario.method.upper():
                endpoint_slice = ep
                break
        if not endpoint_slice:
            return None

        tried_ids = {current_scenario.mutation_id}
        for mut in endpoint_slice.mutations:
            if mut.case_type == case_type and mut.id not in tried_ids:
                return Scenario(
                    endpoint=endpoint,
                    method=current_scenario.method,
                    case_type=case_type,
                    priority=current_scenario.priority,
                    mutation_id=mut.id,
                    expected_status=mut.expected_status,
                )
        return None
