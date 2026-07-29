"""tests/unit/test_generate_ollama_retry.py — GenerateStage's Ollama retry behaviour.

Regression: when Ollama is fully unreachable (ConnectionError), GenerateStage
used to retry the *entire* generation across all 3 temperatures — each retry
paying OllamaClient's own multi-second exponential backoff ladder — before
falling back to the template generator. That's ~3x the wasted time a real
user with no Ollama installed would see per scenario, with no indication
anything is wrong until the fallback kicks in. A connection failure can't be
fixed by trying a different temperature, so GenerateStage should stop after
the first one and fall back immediately. Other kinds of failures (structural
validation, arbitrary exceptions) should keep retrying across temperatures
as before.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
import pytest

from cherenkov.core.contracts import Scenario, Status
from cherenkov.core.errors import LoggerConfig
from cherenkov.stages.generate import GenerateStage


@pytest.fixture(autouse=True)
def _suppress_logging():
    LoggerConfig.suppress_stderr = True
    yield
    LoggerConfig.suppress_stderr = False


@pytest.fixture(autouse=True)
def _no_endpoint_cache():
    """EndpointCache persists to a real sqlite file across process runs —
    force every lookup to miss so these tests are deterministic regardless
    of what's on disk from other runs/tests using the same scenario/path."""
    with patch("cherenkov.cache.endpoint_cache.EndpointCache.get", return_value=None), \
         patch("cherenkov.cache.endpoint_cache.EndpointCache.put", return_value=None):
        yield


def _scenario(mutation_id: str) -> Scenario:
    return Scenario(
        mutation_id=mutation_id,
        endpoint="/test",
        method="GET",
        case_type="happy_path",
        expected_status=200,
    )


class TestOllamaConnectionErrorFallback:
    def test_connection_error_stops_after_first_temperature(self):
        mock_client = MagicMock()
        mock_client.complete_code.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish a new connection: [Errno 111] Connection refused"
        )

        with patch("cherenkov.stages.generate.get_client", return_value=mock_client):
            out = GenerateStage("test-conn-error").run(
                scenario=_scenario("conn_error_scenario"),
                path="/test",
                method="GET",
            )

        assert out.status == Status.OK
        assert out.test_code  # template fallback still produces something
        assert mock_client.complete_code.call_count == 1, (
            "a ConnectionError should not be retried across all 3 temperatures"
        )

    def test_other_exception_still_retries_all_temperatures(self):
        """Non-connection failures (e.g. structural/model errors) keep the
        existing retry-across-temperatures behaviour."""
        mock_client = MagicMock()
        mock_client.complete_code.side_effect = RuntimeError("model returned garbage")

        with patch("cherenkov.stages.generate.get_client", return_value=mock_client):
            out = GenerateStage("test-generic-error").run(
                scenario=_scenario("generic_error_scenario"),
                path="/test",
                method="GET",
            )

        assert out.status == Status.OK
        assert out.test_code
        assert mock_client.complete_code.call_count == 3

    def test_successful_generation_unaffected(self):
        mock_client = MagicMock()
        mock_client.complete_code.return_value = (
            "import { client } from '../client';\n"
            "import { test, expect } from '@playwright/test';\n"
            "test('x', async () => {\n"
            "  const { data, response } = await client.GET('/test', {});\n"
            "  expect(response.status).toBe(200);\n"
            "  expect(data).toHaveProperty('id');\n"
            "});\n"
        )

        with patch("cherenkov.stages.generate.get_client", return_value=mock_client):
            out = GenerateStage("test-success").run(
                scenario=_scenario("success_scenario"),
                path="/test",
                method="GET",
            )

        assert out.status == Status.OK
        assert mock_client.complete_code.call_count == 1
