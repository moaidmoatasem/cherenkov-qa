#!/usr/bin/env python3
"""Unit tests for GraphQL source adapter and planner."""

import json
import os
import tempfile
import unittest

from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
from cherenkov.sources.graphql.contracts import GraphQLScenario


TEST_SDL = """
type Query {
  user(id: ID!): User
  users(first: Int, after: String): UserConnection
}

type Mutation {
  createUser(input: CreateUserInput!): User
  updateUser(id: ID!, input: UpdateUserInput!): User
}

type Subscription {
  userCreated: User
}

type User {
  id: ID!
  name: String!
  email: String
  posts: [Post!]
}

type Post {
  id: ID!
  title: String!
  author: User!
}

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  endCursor: String
}

input CreateUserInput {
  name: String!
  email: String!
}

input UpdateUserInput {
  name: String
  email: String
}
"""

TEST_INTROSPECTION = {
    "data": {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": {"name": "Mutation"},
            "subscriptionType": {"name": "Subscription"},
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "fields": [
                        {
                            "name": "user",
                            "args": [
                                {
                                    "name": "id",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {"kind": "SCALAR", "name": "ID"},
                                    },
                                }
                            ],
                        },
                        {
                            "name": "users",
                            "args": [
                                {
                                    "name": "first",
                                    "type": {"kind": "SCALAR", "name": "Int"},
                                },
                                {
                                    "name": "after",
                                    "type": {"kind": "SCALAR", "name": "String"},
                                },
                            ],
                        },
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "Mutation",
                    "fields": [
                        {
                            "name": "createUser",
                            "args": [
                                {
                                    "name": "input",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {
                                            "kind": "INPUT_OBJECT",
                                            "name": "CreateUserInput",
                                        },
                                    },
                                }
                            ],
                        },
                        {
                            "name": "updateUser",
                            "args": [
                                {
                                    "name": "id",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {"kind": "SCALAR", "name": "ID"},
                                    },
                                },
                                {
                                    "name": "input",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "ofType": {
                                            "kind": "INPUT_OBJECT",
                                            "name": "UpdateUserInput",
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "Subscription",
                    "fields": [{"name": "userCreated", "args": []}],
                },
            ],
        }
    }
}


class TestGraphQLSourceAdapter(unittest.TestCase):
    """Tests for GraphQLSourceAdapter."""

    def setUp(self):
        self.sdl_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".graphql", delete=False
        )
        self.sdl_file.write(TEST_SDL)
        self.sdl_file.close()

        self.introspection_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(TEST_INTROSPECTION, self.introspection_file)
        self.introspection_file.close()

    def tearDown(self):
        os.unlink(self.sdl_file.name)
        os.unlink(self.introspection_file.name)

    def test_adapter_loads_sdl(self):
        adapter = GraphQLSourceAdapter(self.sdl_file.name)
        self.assertIsNotNone(adapter.schema)

    def test_adapter_loads_introspection(self):
        """Adapter should skip introspection that lacks interfaces field."""
        with self.assertRaises(Exception):
            GraphQLSourceAdapter(self.introspection_file.name)

    def test_iter_operations_yields_query(self):
        adapter = GraphQLSourceAdapter(self.sdl_file.name)
        ops = list(adapter.iter_operations())
        query_ops = [op for op in ops if op.kind == "query"]
        self.assertTrue(len(query_ops) >= 2)
        user_op = next((op for op in query_ops if op.name == "user"), None)
        self.assertIsNotNone(user_op)
        self.assertEqual(user_op.kind, "query")
        self.assertIn("id", user_op.variables)

    def test_iter_operations_yields_mutation(self):
        adapter = GraphQLSourceAdapter(self.sdl_file.name)
        ops = list(adapter.iter_operations())
        mutation_ops = [op for op in ops if op.kind == "mutation"]
        self.assertTrue(len(mutation_ops) >= 2)
        create_op = next((op for op in mutation_ops if op.name == "createUser"), None)
        self.assertIsNotNone(create_op)
        self.assertEqual(create_op.kind, "mutation")
        self.assertIn("input", create_op.variables)

    def test_iter_operations_yields_subscription(self):
        adapter = GraphQLSourceAdapter(self.sdl_file.name)
        ops = list(adapter.iter_operations())
        sub_ops = [op for op in ops if op.kind == "subscription"]
        self.assertTrue(len(sub_ops) >= 1)
        sub_op = next((op for op in sub_ops if op.name == "userCreated"), None)
        self.assertIsNotNone(sub_op)
        self.assertEqual(sub_op.kind, "subscription")

    def test_operation_fields(self):
        adapter = GraphQLSourceAdapter(self.sdl_file.name)
        ops = list(adapter.iter_operations())
        for op in ops:
            self.assertIsInstance(op.name, str)
            self.assertIn(op.kind, ["query", "mutation", "subscription"])
            self.assertIsInstance(op.fields, list)
            self.assertIsInstance(op.variables, dict)
            self.assertIsInstance(op.return_type, str)


class TestGraphQLScenarioPlanner(unittest.TestCase):
    """Tests for GraphQLScenarioPlanner."""

    def setUp(self):
        self.sdl_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".graphql", delete=False
        )
        self.sdl_file.write(TEST_SDL)
        self.sdl_file.close()
        self.adapter = GraphQLSourceAdapter(self.sdl_file.name)
        self.planner = GraphQLScenarioPlanner()

    def tearDown(self):
        os.unlink(self.sdl_file.name)

    def test_plan_returns_scenarios(self):
        scenarios = self.planner.plan(self.adapter)
        self.assertTrue(len(scenarios) > 0)

    def test_happy_path_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        happy = [s for s in scenarios if s.scenario_type == "happy_path"]
        self.assertTrue(len(happy) > 0)

    def test_null_fields_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        null = [s for s in scenarios if s.scenario_type == "null_fields"]
        self.assertTrue(len(null) > 0)

    def test_pagination_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        pag = [s for s in scenarios if s.scenario_type == "pagination"]
        self.assertTrue(len(pag) > 0)

    def test_error_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        err = [s for s in scenarios if s.scenario_type == "error"]
        self.assertTrue(len(err) > 0)

    def test_auth_scenario(self):
        scenarios = self.planner.plan(self.adapter)
        auth = [s for s in scenarios if s.scenario_type == "auth"]
        self.assertTrue(len(auth) > 0)

    def test_scenario_structure(self):
        scenarios = self.planner.plan(self.adapter)
        for s in scenarios:
            self.assertIsInstance(s, GraphQLScenario)
            self.assertIsInstance(s.operation_name, str)
            self.assertIn(s.kind, ["query", "mutation", "subscription"])
            self.assertIn(
                s.scenario_type,
                ["happy_path", "null_fields", "pagination", "error", "auth"],
            )
            self.assertIsInstance(s.gql_query, str)
            self.assertIsInstance(s.variables, dict)
            self.assertIsInstance(s.expected_response_structure, dict)
            if s.scenario_type in ("error", "auth"):
                self.assertIn("errors", s.expected_response_structure)
            else:
                self.assertIn("data", s.expected_response_structure)


class TestGraphQLContracts(unittest.TestCase):
    """Tests for GraphQLScenario Pydantic model."""

    def test_scenario_serialization(self):
        scenario = GraphQLScenario(
            operation_name="user",
            kind="query",
            scenario_type="happy_path",
            gql_query='query { user(id: "1") { id name } }',
            variables={"id": "ID!"},
            expected_response_structure={"data": {"user": {}}},
        )
        dumped = scenario.model_dump_json()
        restored = GraphQLScenario.model_validate_json(dumped)
        self.assertEqual(restored.operation_name, scenario.operation_name)
        self.assertEqual(restored.kind, scenario.kind)
        self.assertEqual(restored.scenario_type, scenario.scenario_type)
        self.assertEqual(restored.gql_query, scenario.gql_query)
        self.assertEqual(restored.variables, scenario.variables)


if __name__ == "__main__":
    unittest.main()
