"""
Shared pytest fixtures for the cherenkov test suite.

Provides:
- dev_env: sets CHERENKOV_ENV=development so simulation flags work in all tests
- ensure_port_8000_free: kills stale processes on port 8000 before each test
- Markers for environment-dependent tests (playwright, ollama, gpu)
"""

import socket
import subprocess
import time
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_playwright: test needs Playwright + Node installed"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: test needs a running Ollama instance"
    )
    config.addinivalue_line(
        "markers", "requires_gpu: test needs a GPU runner with qwen2.5-coder"
    )


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def _free_port(port: int, timeout: float = 8.0) -> None:
    """Kill any process holding the given port, then wait for it to be released."""
    try:
        result = subprocess.run(
            ["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _port_in_use(port):
            return
        time.sleep(0.2)


@pytest.fixture(autouse=True)
def dev_env(monkeypatch):
    """Ensure simulation and dev-only flags are enabled for every test."""
    monkeypatch.setenv("CHERENKOV_ENV", "development")


@pytest.fixture(autouse=True)
def ensure_port_8000_free():
    """Before each test, ensure port 8000 is not held by a stale server process."""
    if _port_in_use(8000):
        _free_port(8000)
    yield
    # After the test, give the OS a moment to release the port before the next test.
    if _port_in_use(8000):
        _free_port(8000, timeout=4.0)
