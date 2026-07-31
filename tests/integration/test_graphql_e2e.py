import os

# We can import the script's main by treating the cherenkov package as the root
# But since the root script is cherenkov.py, we can just use runpy
import runpy
import sys
import tempfile
from unittest.mock import MagicMock, patch

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


def _fake_ollama_response():
    """Return a minimal fake requests.Response mimicking Ollama's generate API."""
    fake = MagicMock()
    fake.raise_for_status = MagicMock()
    fake.json.return_value = {
        "response": "// auto-generated graphql test stub",
        "prompt_eval_count": 10,
        "eval_count": 20,
    }
    fake.status_code = 200
    return fake


@patch("cherenkov.cache.endpoint_cache.EndpointCache")
@patch("cherenkov.execution.validate.ValidationEngine.validate_suite")
@patch("cherenkov.ai.ollama_client._post_with_retry", return_value=_fake_ollama_response())
def test_graphql_generate_integration(mock_post, mock_validate, mock_cache):
    mock_validate.return_value = {"status": "ok", "reports": [{"passed": True, "scenario_id": "test", "request_body": "req", "response_body": "res", "response_status": 200}]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".graphql", delete=False) as f:
        f.write(TEST_SDL)
        temp_path = f.name

    old_argv = sys.argv
    try:
        sys.argv = ["cherenkov", "validate", "--source", "graphql", "--spec", temp_path, "--target", "http://mock-target.local"]
        runpy.run_module("cherenkov.cli.core", run_name="__main__")

        mock_validate.assert_called_once()
    except SystemExit as e:
        # argparse or sys.exit might raise SystemExit. Return code 0 is expected.
        assert e.code == 0
    finally:
        sys.argv = old_argv
        os.unlink(temp_path)

