from unittest.mock import patch, MagicMock
import subprocess

# Modify sys.path to allow importing tools/qwen_code_mcp.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from qwen_code_mcp import run_qwen_code_agent, RunQwenCodeAgentArgs


def test_qwen_code_agent_not_installed():
    with patch("shutil.which", return_value=None):
        result = run_qwen_code_agent(RunQwenCodeAgentArgs(prompt="test"))
        assert result["status"] == "error"
        assert "not found in PATH" in result["error"]


def test_qwen_code_agent_success():
    with patch("shutil.which", return_value="/usr/bin/qwen"), patch(
        "subprocess.run"
    ) as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Qwen Code Response"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        args = RunQwenCodeAgentArgs(
            prompt="test prompt", context="test context", files=["a.py"]
        )
        result = run_qwen_code_agent(args)

        assert result["status"] == "success"
        assert result["stdout"] == "Qwen Code Response"

        cmd_args = mock_run.call_args[0][0]
        assert cmd_args[0] == "qwen"
        assert "test prompt" in cmd_args[-1]
        assert "@a.py" in cmd_args[-1]
        assert "test context" in cmd_args[-1]


def test_qwen_code_agent_timeout():
    with patch("shutil.which", return_value="/usr/bin/qwen"), patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="qwen", timeout=120)
    ):
        result = run_qwen_code_agent(RunQwenCodeAgentArgs(prompt="test"))

        assert result["status"] == "error"
        assert "timed out" in result["error"]
