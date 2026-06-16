"""Tests for the AsyncAPI source adapter and planner."""

import tempfile
import os
import yaml
import unittest
from cherenkov.sources.asyncapi.adapter import AsyncAPISourceAdapter
from cherenkov.sources.asyncapi.contracts import AsyncAPIOperation, AsyncAPIScenario
from cherenkov.stages.plan_asyncapi import AsyncAPIScenarioPlanner


SAMPLE_SPEC = {
    "asyncapi": "2.6.0",
    "info": {"title": "Order Events", "version": "1.0.0"},
    "channels": {
        "orders/created": {
            "publish": {
                "message": {
                    "name": "OrderCreated",
                    "contentType": "application/json",
                    "payload": {
                        "type": "object",
                        "required": ["orderId", "userId"],
                        "properties": {
                            "orderId": {"type": "string"},
                            "userId": {"type": "string"},
                            "amount": {"type": "number"},
                        },
                    },
                }
            },
            "subscribe": {
                "message": {
                    "name": "OrderConfirmation",
                    "contentType": "application/json",
                    "payload": {
                        "type": "object",
                        "properties": {
                            "orderId": {"type": "string"},
                            "status": {"type": "string"},
                        },
                    },
                }
            },
        },
        "orders/updated": {
            "publish": {
                "message": {
                    "name": "OrderUpdated",
                    "payload": {
                        "type": "object",
                        "required": ["orderId"],
                        "properties": {
                            "orderId": {"type": "string"},
                            "changes": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                }
            }
        },
    },
}

SAMPLE_SPEC_REF = {
    "asyncapi": "2.6.0",
    "info": {"title": "Ref Test", "version": "1.0.0"},
    "components": {
        "messages": {
            "UserEvent": {
                "name": "UserEvent",
                "payload": {
                    "type": "object",
                    "required": ["userId"],
                    "properties": {
                        "userId": {"type": "string"},
                        "action": {"type": "string"},
                    },
                },
            }
        }
    },
    "channels": {
        "users/events": {
            "publish": {
                "message": {"$ref": "#/components/messages/UserEvent"}
            }
        }
    },
}


class TestAsyncAPIAdapter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write_spec(self, data: dict) -> str:
        path = os.path.join(self.tmpdir, "asyncapi.yaml")
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def test_parses_channels_and_operations(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 3)

    def test_publish_operation_has_correct_channel(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        publish_ops = [op for op in ops if op.channel == "orders/created" and op.operation == "publish"]
        self.assertEqual(len(publish_ops), 1)
        self.assertEqual(publish_ops[0].operation, "publish")

    def test_subscribe_operation_has_message_name(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        sub_ops = [op for op in ops if op.operation == "subscribe"]
        self.assertEqual(len(sub_ops), 1)

    def test_payload_schema_extracted(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        publish_ops = [op for op in ops if op.operation == "publish"]
        self.assertTrue(all(op.payload_schema is not None for op in publish_ops))

    def test_required_fields_in_payload(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        order_created = [op for op in ops if op.message_name == "OrderCreated"]
        self.assertTrue(len(order_created) > 0)
        required = order_created[0].payload_schema.get("required", [])
        self.assertIn("orderId", required)
        self.assertIn("userId", required)

    def test_content_type_default(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        for op in ops:
            self.assertEqual(op.content_type, "application/json")

    def test_resolves_dollar_ref(self):
        path = self._write_spec(SAMPLE_SPEC_REF)
        adapter = AsyncAPISourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        op = ops[0]
        self.assertEqual(op.message_name, "UserEvent")
        self.assertIsNotNone(op.payload_schema)
        required = op.payload_schema.get("required", [])
        self.assertIn("userId", required)

    def test_iter_operations_yields_typed_objects(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        for op in adapter.iter_operations():
            self.assertIsInstance(op, AsyncAPIOperation)
            self.assertTrue(op.channel.startswith("orders/"))
            self.assertIn(op.operation, ("publish", "subscribe"))


class TestAsyncAPIScenarioPlanner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write_spec(self, data: dict) -> str:
        path = os.path.join(self.tmpdir, "asyncapi.yaml")
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def test_planner_generates_scenarios(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        planner = AsyncAPIScenarioPlanner()
        scenarios = planner.plan(adapter)
        self.assertGreater(len(scenarios), 0)

    def test_planner_creates_happy_and_error_scenarios(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        planner = AsyncAPIScenarioPlanner()
        scenarios = planner.plan(adapter)
        types = {s.scenario_type for s in scenarios}
        self.assertIn("happy_path", types)
        self.assertIn("invalid_payload", types)

    def test_planner_adds_missing_required_for_channels_with_required(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        planner = AsyncAPIScenarioPlanner()
        scenarios = planner.plan(adapter)
        missing_req = [s for s in scenarios if s.scenario_type == "missing_required"]
        self.assertGreater(len(missing_req), 0)

    def test_planner_scenarios_are_typed(self):
        path = self._write_spec(SAMPLE_SPEC)
        adapter = AsyncAPISourceAdapter(path)
        planner = AsyncAPIScenarioPlanner()
        for s in planner.plan(adapter):
            self.assertIsInstance(s, AsyncAPIScenario)
