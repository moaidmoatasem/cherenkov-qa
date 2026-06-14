from pydantic import BaseModel


class GraphQLScenario(BaseModel):
    operation_name: str
    kind: str  # query/mutation/subscription
    scenario_type: str  # happy_path | null_fields | pagination | error | auth
    gql_query: str
    variables: dict
    expected_response_structure: dict
