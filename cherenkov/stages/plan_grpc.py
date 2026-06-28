from cherenkov.sources.grpc.adapter import gRPCSourceAdapter, gRPCOperation
from cherenkov.sources.grpc.contracts import gRPCScenario

class gRPCScenarioPlanner:
    def plan(self, adapter: gRPCSourceAdapter) -> list[gRPCScenario]:
        scenarios = []
        for op in adapter.iter_operations():
            scenarios.extend(self._scenarios_for(op))
        return scenarios

    def _scenarios_for(self, op: gRPCOperation) -> list[gRPCScenario]:
        scenarios = []

        # 1. Happy path
        scenarios.append(gRPCScenario(
            service=op.service,
            rpc_name=op.rpc_name,
            input_message=op.input_message,
            proto_content=op.proto_content,
            case_type="happy_path",
            mutation_id=f"grpc_{op.service}_{op.rpc_name}_happy",
            expected_status=200
        ))

        # 2. Missing fields
        scenarios.append(gRPCScenario(
            service=op.service,
            rpc_name=op.rpc_name,
            input_message=op.input_message,
            proto_content=op.proto_content,
            case_type="missing_fields",
            mutation_id=f"grpc_{op.service}_{op.rpc_name}_missing",
            expected_status=400
        ))

        return scenarios
