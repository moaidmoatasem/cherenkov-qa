"""Golden snapshot test for the GENERATE stage.

Mocks the LLM to return a fixed response and asserts:
1. Post-processing (think-block stripping, fence removal) is stable.
2. The generator system prompt hasn't drifted (SHA-256 guard).

To regenerate the snapshot after an intentional prompt/output change:
    python3 tests/test_golden_generate.py --regen
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN_TS = FIXTURES / "golden_generate.ts"
PROMPT_HASH_FILE = FIXTURES / "generator_prompt.sha256"
REPO_ROOT = Path(__file__).parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "generator_system.txt"

# This simulates what OllamaInferenceClient.complete_code() returns AFTER it strips
# markdown fences (```typescript...```) and the caller strips <think> blocks.
# The golden snapshot test verifies GenerateStage post-processing, not the LLM itself.
_MOCK_CLIENT_RESPONSE = """\
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('GET /pets happy_path (status 200)', async () => {
  const { data, response } = await client.GET('/pets', {});
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});"""


def _current_prompt_hash() -> str:
    return hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest()


def test_generator_prompt_hash_unchanged():
    """Fail if prompts/generator_system.txt changes without updating the snapshot."""
    if not PROMPT_FILE.exists():
        pytest.skip("generator_system.txt not found — skipping prompt hash guard")
    recorded = PROMPT_HASH_FILE.read_text().strip()
    actual = _current_prompt_hash()
    assert actual == recorded, (
        f"prompts/generator_system.txt has changed (SHA-256 mismatch).\n"
        f"  Recorded: {recorded}\n"
        f"  Current:  {actual}\n"
        f"If this change is intentional, regenerate the snapshot:\n"
        f"  python3 tests/test_golden_generate.py --regen"
    )


@patch("cherenkov.stages.generate.get_client")
@patch("subprocess.run")
def test_generate_output_matches_golden(mock_subproc, mock_get_client):
    """Assert that the GENERATE stage post-processes LLM output correctly."""
    from cherenkov.core.contracts import Scenario
    from cherenkov.stages.generate import GenerateStage

    mock_client = MagicMock()
    mock_client.complete_code.return_value = _MOCK_CLIENT_RESPONSE
    mock_get_client.return_value = mock_client
    mock_subproc.return_value = MagicMock(returncode=0)

    scenario = Scenario(
        endpoint="/pets",
        method="GET",
        case_type="happy_path",
        mutation_id="golden_mut",
        expected_status=200,
        priority="high",
    )

    stage = GenerateStage("golden_run")
    with patch("cherenkov.cache.endpoint_cache.EndpointCache") as mock_cache_cls:
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache
        output = stage.run(
            scenario=scenario,
            path="/pets",
            method="GET",
            operation={},
            schemas={},
            instruction="Validate happy path for GET /pets",
        )

    assert output.status == "ok", f"GenerateStage failed: {output}"
    assert "<think>" not in output.test_code, "think block not stripped"
    assert "```" not in output.test_code, "markdown fence not stripped"

    expected = GOLDEN_TS.read_text()
    assert output.test_code.strip() == expected.strip(), (
        "GENERATE output has drifted from the golden snapshot.\n"
        "If this is intentional, regenerate:\n"
        "  python3 tests/test_golden_generate.py --regen"
    )


# ── Retry-on-bad-output (#627) ──────────────────────────────────────────────

_BAD_TS = """\
import { client } from '../client';
import { test, expect } from '@playwright/test';
// truncated — unbalanced brace
test('create user happy_path', async () => {
  const { data, response } = await client.POST('/users', {
"""

_GOOD_TS = """\
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy_path', async () => {
  const { data, response } = await client.POST('/users', { body: { email: 'a@b.com', password: 'pw123' } });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});"""


@patch("cherenkov.stages.generate.get_client")
@patch("subprocess.run")
def test_retries_on_structurally_invalid_output(mock_subproc, mock_get_client):
    """Stage must retry when the first attempt returns unbalanced / test()-less TS."""
    from cherenkov.core.contracts import Scenario
    from cherenkov.stages.generate import GenerateStage

    mock_client = MagicMock()
    # First call returns badly-formed code; second call returns valid code.
    mock_client.complete_code.side_effect = [_BAD_TS, _GOOD_TS]
    mock_get_client.return_value = mock_client
    mock_subproc.return_value = MagicMock(returncode=0)

    scenario = Scenario(
        endpoint="/users",
        method="POST",
        case_type="happy_path",
        mutation_id="retry_mut",
        expected_status=201,
        priority="high",
    )

    stage = GenerateStage("retry_run")
    with patch("cherenkov.cache.endpoint_cache.EndpointCache") as mock_cache_cls:
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache
        output = stage.run(
            scenario=scenario,
            path="/users",
            method="POST",
            operation={},
            schemas={},
            instruction="Create user happy path",
        )

    assert output.status == "ok", f"expected ok, got {output.status}: {getattr(output, 'errors', '')}"
    assert mock_client.complete_code.call_count == 2, "should have retried once"
    assert "test(" in output.test_code
    assert output.test_code.count("{") == output.test_code.count("}")


if __name__ == "__main__":
    import sys

    if "--regen" in sys.argv:
        from unittest.mock import MagicMock as _MM
        from unittest.mock import patch as _patch

        with _patch("cherenkov.stages.generate.get_client") as mc, \
             _patch("subprocess.run") as ms, \
             _patch("cherenkov.cache.endpoint_cache.EndpointCache") as mcc:
            from cherenkov.core.contracts import Scenario
            from cherenkov.stages.generate import GenerateStage

            _mock = _MM()
            _mock.complete_code.return_value = _MOCK_CLIENT_RESPONSE
            mc.return_value = _mock
            ms.return_value = _MM(returncode=0)
            _cache = _MM()
            _cache.get.return_value = None
            mcc.return_value = _cache

            sc = Scenario(
                endpoint="/pets", method="GET", case_type="happy_path",
                mutation_id="golden_mut", expected_status=200, priority="high",
            )
            out = GenerateStage("regen").run(
                scenario=sc, path="/pets", method="GET",
                operation={}, schemas={}, instruction="Validate happy path for GET /pets",
            )
        GOLDEN_TS.write_text(out.test_code.strip() + "\n")
        PROMPT_HASH_FILE.write_text(_current_prompt_hash() + "\n")
        print(f"Regenerated {GOLDEN_TS} and {PROMPT_HASH_FILE}")
    else:
        pytest.main([__file__, "-v"])
