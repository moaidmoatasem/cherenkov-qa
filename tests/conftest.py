"""
Shared pytest fixtures for the cherenkov test suite.

Provides:
- dev_env: sets CHERENKOV_ENV=development so simulation flags work in all tests
- Markers for environment-dependent tests (playwright, ollama, gpu)
"""
import os
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_playwright: test needs Playwright + Node installed")
    config.addinivalue_line("markers", "requires_ollama: test needs a running Ollama instance")
    config.addinivalue_line("markers", "requires_gpu: test needs a GPU runner with qwen2.5-coder")


@pytest.fixture(autouse=True)
def dev_env(monkeypatch):
    """Ensure simulation and dev-only flags are enabled for every test."""
    monkeypatch.setenv("CHERENKOV_ENV", "development")
