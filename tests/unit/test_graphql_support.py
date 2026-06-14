"""Unit tests for GraphQL source adapter and scenario planner."""

import unittest
import tempfile
import json


def _make_sdl(content: str) -> str:
    """Write SDL content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".graphql", delete=False)
    f.write(content)
    f.close()
    return f.name


def _make_introspection(schema_str: str) -> str:
    """Build an introspection JSON file from SDL and return the path."""
    from graphql import build_ast_schema, parse, introspection_from_schema
    schema = build_ast_schema(parse(schema_str))
    result = introspection_from_schema(schema)
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(result, f)
    f.close()
    return f.name


class TestGraphQLSourceAdapter(unittest.TestCase):

    def test_sdl_parses_basic_query(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        path = _make_sdl("type Query { hello: String }")
        adapter = GraphQLSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].name, "hello")
        self.assertEqual(ops[0].kind, "query")

    def test_introspection_parses(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        path = _make_introspection("type Query { hello: String }")
        adapter = GraphQLSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].name, "hello")

    def test_iter_operations_yields_all_root_types(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        sdl = """
        type Query { hello: String }
        type Mutation { createUser(name: String!): String }
        type Subscription { onUserCreated: String }
        """
        path = _make_sdl(sdl)
        adapter = GraphQLSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 3)
        kinds = [op.kind for op in ops]
        self.assertIn("query", kinds)
        self.assertIn("mutation", kinds)
        self.assertIn("subscription", kinds)

    def test_leaf_fields_resolves_nested_types(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        sdl = """
        type Query { user: User }
        type User { id: ID! name: String email: String }
        """
        path = _make_sdl(sdl)
        adapter = GraphQLSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        fields = ops[0].fields
        self.assertIn("id", fields)
        self.assertIn("name", fields)
        self.assertIn("email", fields)

    def test_leaf_fields_resolves_list_types(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        sdl = """
        type Query { users: [User] }
        type User { id: ID! name: String }
        """
        path = _make_sdl(sdl)
        adapter = GraphQLSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        self.assertIn("id", ops[0].fields)
        self.assertIn("name", ops[0].fields)

    def test_variables_are_extracted(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        sdl = 'type Query { user(id: ID! name: String): String }'
        path = _make_sdl(sdl)
        adapter = GraphQLSourceAdapter(path)
        ops = list(adapter.iter_operations())
        self.assertEqual(len(ops), 1)
        self.assertIn("id", ops[0].variables)
        self.assertIn("name", ops[0].variables)

    def test_empty_schema_yields_no_operations(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        sdl = """
        type Query { hello: String }
        """
        # Remove Query type entirely
        from graphql import build_ast_schema, parse
        schema = build_ast_schema(parse(sdl))
        del schema.type_map["Query"]
        import cherenkov.sources.graphql.adapter as mod
        adapter = mod.GraphQLSourceAdapter.__new__(mod.GraphQLSourceAdapter)
        adapter.schema = schema
        ops = list(adapter.iter_operations())
        self.assertEqual(ops, [])


class TestGraphQLScenarioPlanner(unittest.TestCase):

    def test_plan_creates_happy_path_scenario(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        path = _make_sdl("type Query { hello: String }")
        adapter = GraphQLSourceAdapter(path)
        planner = GraphQLScenarioPlanner()
        scenarios = planner.plan(adapter)
        self.assertGreater(len(scenarios), 0)
        types = [s.scenario_type for s in scenarios]
        self.assertIn("happy_path", types)

    def test_plan_creates_error_and_auth_scenarios(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        path = _make_sdl("type Query { hello: String }")
        adapter = GraphQLSourceAdapter(path)
        planner = GraphQLScenarioPlanner()
        scenarios = planner.plan(adapter)
        types = [s.scenario_type for s in scenarios]
        self.assertIn("error", types)
        self.assertIn("auth", types)
        self.assertIn("null_fields", types)

    def test_plan_creates_pagination_with_limit(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        sdl = "type Query { items(first: Int after: String): [String] }"
        path = _make_sdl(sdl)
        adapter = GraphQLSourceAdapter(path)
        planner = GraphQLScenarioPlanner()
        scenarios = planner.plan(adapter)
        types = [s.scenario_type for s in scenarios]
        self.assertIn("pagination", types)

    def test_plan_skips_pagination_without_cursor_args(self):
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        path = _make_sdl("type Query { hello: String }")
        adapter = GraphQLSourceAdapter(path)
        planner = GraphQLScenarioPlanner()
        scenarios = planner.plan(adapter)
        types = [s.scenario_type for s in scenarios]
        self.assertNotIn("pagination", types)


if __name__ == "__main__":
    unittest.main()
