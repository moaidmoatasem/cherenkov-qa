"""Unit tests for gRPC source adapter and scenario planner."""

import unittest
import tempfile


def _make_proto(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".proto", delete=False)
    f.write(content)
    f.close()
    return f.name


SIMPLE_PROTO = """
syntax = "proto3";
service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply) {}
}
message HelloRequest { string name = 1; }
message HelloReply { string message = 1; }
"""

MULTI_SERVICE_PROTO = """
syntax = "proto3";
service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply) {}
  rpc SayGoodbye (GoodbyeRequest) returns (GoodbyeReply) {}
}
service Admin {
  rpc Ping (PingRequest) returns (PongReply) {}
}
message HelloRequest { string name = 1; }
message HelloReply { string message = 1; }
message GoodbyeRequest { string name = 1; }
message GoodbyeReply { string message = 1; }
message PingRequest {}
message PongReply { string ok = 1; }
"""


class TestgRPCSourceAdapter(unittest.TestCase):

    def test_parses_single_service_single_rpc(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].service, "Greeter")
        self.assertEqual(ops[0].rpc_name, "SayHello")

    def test_parses_multi_service_multi_rpc(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        path = _make_proto(MULTI_SERVICE_PROTO)
        adapter = gRPCSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 3)

    def test_extracts_input_output_messages(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertIn("HelloRequest", ops[0].input_message)
        self.assertIn("HelloReply", ops[0].output_message)

    def test_proto_content_is_stored(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertIn("service Greeter", ops[0].proto_content)
        self.assertIn("rpc SayHello", ops[0].proto_content)

    def test_empty_proto_yields_no_operations(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        path = _make_proto("")
        adapter = gRPCSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(ops, [])

    def test_proto_with_no_service_yields_no_operations(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        path = _make_proto("message Foo {}")
        adapter = gRPCSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(ops, [])


class TestgRPCScenarioPlanner(unittest.TestCase):

    def test_plan_creates_happy_path_scenario(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        planner = gRPCScenarioPlanner()
        scenarios = planner.plan(adapter)
        self.assertGreater(len(scenarios), 0)
        types = [s.case_type for s in scenarios]
        self.assertIn("happy_path", types)

    def test_plan_creates_missing_fields_scenario(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        planner = gRPCScenarioPlanner()
        scenarios = planner.plan(adapter)
        types = [s.case_type for s in scenarios]
        self.assertIn("missing_fields", types)

    def test_plan_creates_two_scenarios_per_rpc(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        planner = gRPCScenarioPlanner()
        scenarios = planner.plan(adapter)
        self.assertEqual(len(scenarios), 2)

    def test_plan_creates_correct_mutation_ids(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        planner = gRPCScenarioPlanner()
        scenarios = planner.plan(adapter)
        happy = [s for s in scenarios if s.case_type == "happy_path"][0]
        self.assertEqual(happy.mutation_id, "grpc_Greeter_SayHello_happy")
        missing = [s for s in scenarios if s.case_type == "missing_fields"][0]
        self.assertEqual(missing.mutation_id, "grpc_Greeter_SayHello_missing")

    def test_plan_expected_status_correct(self):
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        path = _make_proto(SIMPLE_PROTO)
        adapter = gRPCSourceAdapter(path)
        planner = gRPCScenarioPlanner()
        scenarios = planner.plan(adapter)
        happy = [s for s in scenarios if s.case_type == "happy_path"][0]
        self.assertEqual(happy.expected_status, 200)
        missing = [s for s in scenarios if s.case_type == "missing_fields"][0]
        self.assertEqual(missing.expected_status, 400)


if __name__ == "__main__":
    unittest.main()
