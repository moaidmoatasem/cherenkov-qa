"""AsyncAPI scenario planner."""

from cherenkov.sources.asyncapi.adapter import AsyncAPISourceAdapter
from cherenkov.sources.asyncapi.contracts import AsyncAPIScenario


class AsyncAPIScenarioPlanner:
    def plan(self, adapter: AsyncAPISourceAdapter) -> list[AsyncAPIScenario]:
        scenarios = []
        for op in adapter.iter_operations():
            scenarios.extend(self._scenarios_for(op))
        return scenarios

    def _scenarios_for(self, op) -> list[AsyncAPIScenario]:
        scenarios = []
        required = (
            list(op.payload_schema.get("required", [])) if op.payload_schema else []
        )

        scenarios.append(
            AsyncAPIScenario(
                channel=op.channel,
                operation=op.operation,
                scenario_type="happy_path",
                message=op.message_name,
                expected_status=200,
                required_fields=required,
            )
        )

        if required:
            scenarios.append(
                AsyncAPIScenario(
                    channel=op.channel,
                    operation=op.operation,
                    scenario_type="missing_required",
                    message=op.message_name,
                    expected_status=400,
                    required_fields=required,
                )
            )

        scenarios.append(
            AsyncAPIScenario(
                channel=op.channel,
                operation=op.operation,
                scenario_type="invalid_payload",
                message=op.message_name,
                expected_status=422,
                required_fields=required,
            )
        )

        scenarios.append(
            AsyncAPIScenario(
                channel=op.channel,
                operation=op.operation,
                scenario_type="auth",
                message=op.message_name,
                expected_status=401,
                required_fields=required,
            )
        )

        return scenarios
