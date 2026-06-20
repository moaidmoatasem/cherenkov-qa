import os
import sys
import tempfile
from unittest.mock import patch
import runpy

TEST_PROTO = """
syntax = "proto3";

package users;

service UserService {
  rpc GetUser (GetUserRequest) returns (User);
}

message GetUserRequest {
  string user_id = 1;
}

message User {
  string id = 1;
  string name = 2;
}
"""

@patch("cherenkov.cache.endpoint_cache.EndpointCache")
@patch("cherenkov.execution.validate.ValidationEngine.validate_suite")
def test_grpc_generate_integration(mock_validate, mock_cache):
    mock_validate.return_value = {"status": "ok", "reports": [{"passed": True, "scenario_id": "test", "request_body": "req", "response_body": "res", "response_status": 200}]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".proto", delete=False) as f:
        f.write(TEST_PROTO)
        temp_path = f.name

    old_argv = sys.argv
    try:
        sys.argv = ["cherenkov", "validate", "--source", "grpc", "--spec", temp_path, "--target", "grpc://mock-target.local:50051"]
        runpy.run_module("cherenkov.cli.core", run_name="__main__")
        
        mock_validate.assert_called_once()
    except SystemExit as e:
        assert e.code == 0
    finally:
        sys.argv = old_argv
        os.unlink(temp_path)
