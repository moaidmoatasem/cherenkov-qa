#!/usr/bin/env python3
"""Unit tests for gRPC source adapter and planner."""

import os
import tempfile
import unittest

from cherenkov.sources.grpc.adapter import gRPCSourceAdapter, gRPCOperation
from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
from cherenkov.sources.grpc.contracts import gRPCScenario


TEST_PROTO = """
syntax = "proto3";

package users;

service UserService {
  rpc GetUser (GetUserRequest) returns (User);
  rpc ListUsers (ListUsersRequest) returns (UserList);
}

service HealthService {
  rpc Check (HealthCheckRequest) returns (HealthCheckResponse);
}

message GetUserRequest {
  string user_id = 1;
}

message User {
  string id = 1;
  string name = 2;
  string email = 3;
}

message ListUsersRequest {
  int32 page = 1;
  int32 limit = 2;
}

message UserList {
  repeated User users = 1;
  int32 total = 2;
}

message HealthCheckRequest {
  string service = 1;
}

message HealthCheckResponse {
  string status = 1;
}
"""


class TestGRPCSourceAdapter(unittest.TestCase):
    """Tests for gRPCSourceAdapter."""

    def setUp(self):
        self.proto_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".proto", delete=False
        )
        self.proto_file.write(TEST_PROTO)
        self.proto_file.close()

    def tearDown(self):
        os.unlink(self.proto_file.name)

    def test_adapter_loads_proto(self):
        adapter = gRPCSourceAdapter(self.proto_file.name)
        self.assertIsNotNone(adapter.proto_content)
        self.assertIn('syntax = "proto3"', adapter.proto_content)

    def test_iter_operations_returns_grpc_ops(self):
        adapter = gRPCSourceAdapter(self.proto_file.name)
        ops = list(adapter.iter_operations())
        self.assertTrue(len(ops) > 0)
        for op in ops:
            self.assertIsInstance(op, gRPCOperation)

    def test_parse_service_and_rpc(self):
        adapter = gRPCSourceAdapter(self.proto_file.name)
        ops = list(adapter.iter_operations())

        user_svc_ops = [op for op in ops if op.service == "UserService"]
        self.assertEqual(len(user_svc_ops), 2)

        get_user = next((op for op in user_svc_ops if op.rpc_name == "GetUser"), None)
        self.assertIsNotNone(get_user)
        self.assertIn("GetUserRequest", get_user.input_message)
        self.assertIn("User", get_user.output_message)

    def test_multiple_services(self):
        adapter = gRPCSourceAdapter(self.proto_file.name)
        ops = list(adapter.iter_operations())

        services = set(op.service for op in ops)
        self.assertIn("UserService", services)
        self.assertIn("HealthService", services)

    def test_operation_attributes(self):
        adapter = gRPCSourceAdapter(self.proto_file.name)
        ops = list(adapter.iter_operations())

        for op in ops:
            self.assertIsInstance(op.service, str)
            self.assertIsInstance(op.rpc_name, str)
            self.assertIsInstance(op.input_message, str)
            self.assertIsInstance(op.output_message, str)
            self.assertIsInstance(op.proto_content, str)
            self.assertGreater(len(op.proto_content), 0)

    def test_handles_missing_file_gracefully(self):
        with self.assertRaises(FileNotFoundError):
            gRPCSourceAdapter("/nonexistent/file.proto")


class TestGRPCScenarioPlanner(unittest.TestCase):
    """Tests for gRPCScenarioPlanner."""

    def setUp(self):
        self.proto_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".proto", delete=False
        )
        self.proto_file.write(TEST_PROTO)
        self.proto_file.close()
        self.adapter = gRPCSourceAdapter(self.proto_file.name)
        self.planner = gRPCScenarioPlanner()

    def tearDown(self):
        os.unlink(self.proto_file.name)

    def test_plan_returns_scenarios(self):
        scenarios = self.planner.plan(self.adapter)
        self.assertTrue(len(scenarios) > 0)

    def test_happy_path_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        happy = [s for s in scenarios if s.case_type == "happy_path"]
        self.assertTrue(len(happy) > 0)
        for s in happy:
            self.assertEqual(s.expected_status, 200)

    def test_missing_fields_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        missing = [s for s in scenarios if s.case_type == "missing_fields"]
        self.assertTrue(len(missing) > 0)
        for s in missing:
            self.assertEqual(s.expected_status, 400)

    def test_scenario_attributes(self):
        scenarios = self.planner.plan(self.adapter)
        for s in scenarios:
            self.assertIsInstance(s, gRPCScenario)
            self.assertIsInstance(s.service, str)
            self.assertIsInstance(s.rpc_name, str)
            self.assertIsInstance(s.input_message, str)
            self.assertIsInstance(s.case_type, str)
            self.assertIn(s.case_type, ["happy_path", "missing_fields"])
            self.assertIn(s.expected_status, [200, 400])

    def test_scenario_per_operation(self):
        scenarios = self.planner.plan(self.adapter)
        unique_rpcs = set((s.service, s.rpc_name) for s in scenarios)
        self.assertIn(("UserService", "GetUser"), unique_rpcs)
        self.assertIn(("UserService", "ListUsers"), unique_rpcs)
        self.assertIn(("HealthService", "Check"), unique_rpcs)


class TestGRPCContracts(unittest.TestCase):
    """Tests for gRPCScenario Pydantic model."""

    def test_scenario_serialization(self):
        scenario = gRPCScenario(
            service="UserService",
            rpc_name="GetUser",
            input_message="GetUserRequest",
            proto_content='syntax = "proto3";',
            case_type="happy_path",
            mutation_id="grpc_UserService_GetUser_happy",
            expected_status=200,
        )
        dumped = scenario.model_dump_json()
        restored = gRPCScenario.model_validate_json(dumped)
        self.assertEqual(restored.service, scenario.service)
        self.assertEqual(restored.rpc_name, scenario.rpc_name)
        self.assertEqual(restored.case_type, scenario.case_type)
        self.assertEqual(restored.expected_status, scenario.expected_status)


if __name__ == "__main__":
    unittest.main()
