from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter, GraphQLOperation
from cherenkov.sources.graphql.contracts import GraphQLScenario

class GraphQLScenarioPlanner:
    def plan(self, adapter: GraphQLSourceAdapter) -> list[GraphQLScenario]:
        scenarios = []
        for op in adapter.iter_operations():
            scenarios.extend(self._scenarios_for(op))
        return scenarios

    def _scenarios_for(self, op: GraphQLOperation) -> list[GraphQLScenario]:
        scenarios = []
        
        # 1. Happy path
        query_str = f"{op.kind} {op.name} {{ {op.name} {{ {' '.join(op.fields)} }} }}"
        scenarios.append(GraphQLScenario(
            operation_name=op.name,
            kind=op.kind,
            scenario_type="happy_path",
            gql_query=query_str,
            variables=op.variables,
            expected_response_structure={"data": {op.name: "..."}}
        ))
        
        # 2. Null fields
        scenarios.append(GraphQLScenario(
            operation_name=op.name,
            kind=op.kind,
            scenario_type="null_fields",
            gql_query=query_str,
            variables=op.variables,
            expected_response_structure={"data": {op.name: "..."}}
        ))
        
        # 3. Pagination (if applicable)
        if "first" in op.variables or "after" in op.variables or "limit" in op.variables:
            scenarios.append(GraphQLScenario(
                operation_name=op.name,
                kind=op.kind,
                scenario_type="pagination",
                gql_query=query_str,
                variables=op.variables,
                expected_response_structure={"data": {op.name: "..."}}
            ))
            
        # 4. Error
        scenarios.append(GraphQLScenario(
            operation_name=op.name,
            kind=op.kind,
            scenario_type="error",
            gql_query=query_str,
            variables={}, # invalid args
            expected_response_structure={"errors": []}
        ))
        
        # 5. Auth
        scenarios.append(GraphQLScenario(
            operation_name=op.name,
            kind=op.kind,
            scenario_type="auth",
            gql_query=query_str,
            variables=op.variables,
            expected_response_structure={"errors": []}
        ))
        
        return scenarios
