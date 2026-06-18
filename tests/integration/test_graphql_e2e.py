import os
import sys
import tempfile
from unittest.mock import patch

# We can import the script's main by treating the cherenkov package as the root
# But since the root script is cherenkov.py, we can just use runpy
import runpy

TEST_SDL = """
type Query {
  user(id: ID!): User
}

type Mutation {
  createUser(input: CreateUserInput!): User
}

type User {
  id: ID!
  name: String!
}

input CreateUserInput {
  name: String!
}
"""

@patch("cherenkov.cache.endpoint_cache.EndpointCache")
@patch("cherenkov.execution.validate.ValidationEngine.validate_suite")
def test_graphql_generate_integration(mock_validate, mock_cache):
    mock_validate.return_value = {"status": "ok", "reports": [{"passed": True, "scenario_id": "test", "request_body": "req", "response_body": "res", "response_status": 200}]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".graphql", delete=False) as f:
        f.write(TEST_SDL)
        temp_path = f.name

    old_argv = sys.argv
    try:
        sys.argv = ["cherenkov.py", "validate", "--source", "graphql", "--spec", temp_path, "--target", "http://mock-target.local"]
        # runpy runs the script as __main__
        runpy.run_path("cherenkov.py", run_name="__main__")
        
        mock_validate.assert_called_once()
    except SystemExit as e:
        # argparse or sys.exit might raise SystemExit. Return code 0 is expected.
        assert e.code == 0
    finally:
        sys.argv = old_argv
        os.unlink(temp_path)
