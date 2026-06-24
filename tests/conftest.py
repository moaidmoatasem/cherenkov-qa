from __future__ import annotations
import os
import pytest

os.environ.setdefault("CHERENKOV_RATE_LIMIT_ENABLED", "false")

@pytest.fixture(autouse=True)
def _restore_logger_config():
    from cherenkov.core.errors import LoggerConfig
    original = LoggerConfig.suppress_stderr
    yield
    LoggerConfig.suppress_stderr = original
