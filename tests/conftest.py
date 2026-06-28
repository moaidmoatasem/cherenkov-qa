from __future__ import annotations

import os

import pytest

os.environ.setdefault("CHERENKOV_RATE_LIMIT_ENABLED", "false")


def _ollama_reachable() -> bool:
    try:
        import json as _json
        import urllib.request

        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        resp = urllib.request.urlopen(req, timeout=2)
        data = _json.loads(resp.read().decode())
        return len(data.get("models", [])) > 0
    except Exception:
        return False


ollama_available = _ollama_reachable()


def pytest_configure(config):
    config.addinivalue_line("markers", "ollama: requires Ollama running on localhost:11434")


def pytest_collection_modifyitems(config, items):
    if ollama_available:
        return
    for item in items:
        if "test_judge_sample" in item.nodeid:
            item.add_marker(pytest.mark.skip(reason="Ollama not reachable (needed by LLM-judge evals)"))


@pytest.fixture(autouse=True)
def _restore_logger_config():
    from cherenkov.core.errors import LoggerConfig
    original = LoggerConfig.suppress_stderr
    yield
    LoggerConfig.suppress_stderr = original
