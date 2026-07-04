"""tests/unit/test_self_test_cmd.py — exit-code contract of `cherenkov self-test`.

self-test is a live smoke test (real Ollama + tsc); these tests pin that a
failing first step (Ollama unreachable) exits nonzero and never proceeds to
generation.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from cherenkov.stages.self_test_cmd import run_self_test


def test_returns_1_when_ollama_unreachable(capsys):
    with patch(
        "cherenkov.stages.self_test_cmd.requests.get",
        side_effect=ConnectionError("connection refused"),
    ):
        rc = run_self_test()
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "[2/3]" not in out  # must stop at the first failing step


def test_returns_1_when_ollama_returns_http_error(capsys):
    resp = MagicMock()
    resp.raise_for_status.side_effect = RuntimeError("500 Server Error")
    with patch("cherenkov.stages.self_test_cmd.requests.get", return_value=resp):
        rc = run_self_test()
    assert rc == 1
    assert "FAILED" in capsys.readouterr().out
