"""Unit tests for GitHub Actions entrypoint.sh integration."""
import os
import sys
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

class TestGitHubAction(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for the test execution context
        self.test_dir = tempfile.mkdtemp()
        self.project_root = Path(__file__).resolve().parents[2]
        self.entrypoint_path = self.project_root / "entrypoint.sh"
        self.calls_file = Path(self.test_dir) / "calls.json"
        self.github_output_file = Path(self.test_dir) / "github_output.txt"
        
        # Create a dummy python script inside the temp directory
        self.dummy_python = Path(self.test_dir) / "python"
        
        dummy_content = f"""#!/usr/bin/env python3
import sys
import json
import os

# Record the call
call_info = {{
    "args": sys.argv[1:],
    "env": {{k: v for k, v in os.environ.items() if k.startswith("INPUT_") or k in ("GITHUB_ACTIONS", "GITHUB_OUTPUT")}},
}}

# Read existing calls
calls = []
if os.path.exists("{self.calls_file.as_posix()}"):
    with open("{self.calls_file.as_posix()}", "r") as f:
        try:
            calls = json.load(f)
        except Exception:
            pass

calls.append(call_info)
with open("{self.calls_file.as_posix()}", "w") as f:
    json.dump(calls, f, indent=2)

# Provide mock outputs based on arguments
args_str = " ".join(sys.argv)
if "validate" in args_str and "junit" in args_str:
    print('<?xml version="1.0" encoding="UTF-8"?><testsuites><testsuite name="cherenkov" failures="1"></testsuite></testsuites>')
elif "validate" in args_str and "sarif" in args_str:
    if os.environ.get("MOCK_ZERO_VIOLATIONS") == "true":
        print(json.dumps({{"runs": [{{"results": []}}]}}))
    else:
        print(json.dumps({{"runs": [{{"results": [{{"ruleId": "drift"}}]}}]}}))
elif "-c" in sys.argv:
    code = sys.argv[sys.argv.index("-c") + 1]
    if "OrchestrationEngine" in code:
        sys.exit(0)
    elif "cherenkov-sarif.json" in code:
        import os
        if os.path.exists("cherenkov-sarif.json"):
            with open("cherenkov-sarif.json") as f:
                data = json.load(f)
            print(len(data["runs"][0]["results"]))
        else:
            print(0)
        sys.exit(0)
    else:
        sys.exit(0)
else:
    print("Mock CLI output")
"""
        self.dummy_python.write_text(dummy_content)
        self.dummy_python.chmod(0o755)

        # Setup environment
        self.env = os.environ.copy()
        # Prepend the test_dir to PATH so the dummy python is executed
        self.env["PATH"] = f"{self.test_dir}{os.path.pathsep}{self.env.get('PATH', '')}"
        self.env["GITHUB_OUTPUT"] = str(self.github_output_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def get_calls(self):
        if self.calls_file.exists():
            with open(self.calls_file, "r") as f:
                return json.load(f)
        return []

    def get_github_outputs(self):
        outputs = {}
        if self.github_output_file.exists():
            with open(self.github_output_file, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        outputs[k] = v
        return outputs

    def test_transparent_cli_wrapper(self):
        """Verify that when GITHUB_ACTIONS is not true and INPUT_SPEC is empty, arguments are forwarded transparently."""
        # Unset GHA env vars
        self.env.pop("GITHUB_ACTIONS", None)
        self.env.pop("INPUT_SPEC", None)
        
        # Run entrypoint.sh with custom args
        result = subprocess.run(
            [str(self.entrypoint_path), "validate", "--some-arg", "value"],
            cwd=self.test_dir,
            env=self.env,
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Mock CLI output", result.stdout)
        
        # Assert that python was called exactly once with the forwarded args
        calls = self.get_calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["args"], ["cherenkov.py", "validate", "--some-arg", "value"])

    def test_github_actions_pipeline_with_generation(self):
        """Verify that entrypoint.sh runs the GHA pipeline and performs generation when no spec tests exist."""
        self.env["GITHUB_ACTIONS"] = "true"
        self.env["INPUT_SPEC"] = "openapi.yaml"
        self.env["INPUT_TARGET"] = "http://localhost:8080"
        self.env["INPUT_FAIL_ON_DRIFT"] = "true"
        self.env["INPUT_LLM_PROVIDER"] = "openai"
        
        result = subprocess.run(
            [str(self.entrypoint_path)],
            cwd=self.test_dir,
            env=self.env,
            capture_output=True,
            text=True
        )
        
        # Should fail (exit 1) because of simulated drift (1 violation from mock SARIF)
        self.assertEqual(result.returncode, 1, msg=f"stdout: {result.stdout}\nstderr: {result.stderr}")
        
        # Verify GHA pipeline output and outputs
        outputs = self.get_github_outputs()
        self.assertEqual(outputs.get("violations"), "1")
        self.assertEqual(outputs.get("report-path"), "cherenkov-junit.xml")
        self.assertEqual(outputs.get("sarif-path"), "cherenkov-sarif.json")
        
        # Verify the calls to python
        calls = self.get_calls()
        # Expected calls:
        # 1. init: cherenkov.py init --profile ci --force
        # 2. generate: -c ...
        # 3. validate junit: cherenkov.py validate --target ... --spec ... --output-format junit
        # 4. validate sarif: cherenkov.py validate --target ... --spec ... --output-format sarif
        self.assertEqual(len(calls), 5, msg=f"Calls: {json.dumps(calls, indent=2)}")
        self.assertEqual(calls[0]["args"], ["cherenkov.py", "init", "--profile", "ci", "--force"])
        self.assertEqual(calls[1]["args"][0], "-c")
        self.assertEqual(calls[2]["args"], ["cherenkov.py", "validate", "--target", "http://localhost:8080", "--spec", "openapi.yaml", "--output-format", "junit"])
        self.assertEqual(calls[3]["args"], ["cherenkov.py", "validate", "--target", "http://localhost:8080", "--spec", "openapi.yaml", "--output-format", "sarif"])
        self.assertEqual(calls[4]["args"][0], "-c")

    def test_github_actions_pipeline_without_generation(self):
        """Verify that entrypoint.sh skips generation if spec tests are already present."""
        self.env["GITHUB_ACTIONS"] = "true"
        self.env["INPUT_SPEC"] = "openapi.yaml"
        self.env["INPUT_TARGET"] = "http://localhost:8080"
        self.env["INPUT_FAIL_ON_DRIFT"] = "true"
        self.env["INPUT_LLM_PROVIDER"] = "openai"
        self.env["MOCK_ZERO_VIOLATIONS"] = "true"  # Ensure it exits 0
        
        # Create dummy pre-generated spec test files
        generated_dir = Path(self.test_dir) / "stub" / "generated_tests"
        generated_dir.mkdir(parents=True, exist_ok=True)
        (generated_dir / "api.spec.ts").write_text("// dummy spec test")
        
        result = subprocess.run(
            [str(self.entrypoint_path)],
            cwd=self.test_dir,
            env=self.env,
            capture_output=True,
            text=True
        )
        
        # Should succeed (exit 0) since mock has 0 violations
        self.assertEqual(result.returncode, 0)
        
        # Verify GHA output
        outputs = self.get_github_outputs()
        self.assertEqual(outputs.get("violations"), "0")
        
        # Verify calls: init and generation should have been skipped!
        # Only the two validate calls should be present
        calls = self.get_calls()
        self.assertEqual(len(calls), 3, msg=f"Calls: {json.dumps(calls, indent=2)}")
        self.assertEqual(calls[0]["args"], ["cherenkov.py", "validate", "--target", "http://localhost:8080", "--spec", "openapi.yaml", "--output-format", "junit"])
        self.assertEqual(calls[1]["args"], ["cherenkov.py", "validate", "--target", "http://localhost:8080", "--spec", "openapi.yaml", "--output-format", "sarif"])
        self.assertEqual(calls[2]["args"][0], "-c")

    def test_github_actions_fail_on_drift_disabled(self):
        """Verify that when fail-on-drift is false, the action succeeds even if there are drift violations."""
        self.env["GITHUB_ACTIONS"] = "true"
        self.env["INPUT_SPEC"] = "openapi.yaml"
        self.env["INPUT_TARGET"] = "http://localhost:8080"
        self.env["INPUT_FAIL_ON_DRIFT"] = "false"
        
        # Skip generation
        generated_dir = Path(self.test_dir) / "stub" / "generated_tests"
        generated_dir.mkdir(parents=True, exist_ok=True)
        (generated_dir / "api.spec.ts").write_text("// dummy spec test")
        
        result = subprocess.run(
            [str(self.entrypoint_path)],
            cwd=self.test_dir,
            env=self.env,
            capture_output=True,
            text=True
        )
        
        # Should succeed (exit 0) because fail-on-drift is false
        self.assertEqual(result.returncode, 0)
        
        outputs = self.get_github_outputs()
        self.assertEqual(outputs.get("violations"), "1")
