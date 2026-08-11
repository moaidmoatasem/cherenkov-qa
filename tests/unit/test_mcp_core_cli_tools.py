"""Tests for the cherenkov/* MCP tool handlers in cherenkov.mcp.tools.core_cli.

This module registers three MCP tools — `cherenkov/check-suite`, `cherenkov/verify`
and `cherenkov/generate` — and had no test of its own. The suite in
`test_mcp_tools_depth.py` covers the separately-registered `check_suite` tool in
`handlers.py`, which is a different handler, so nothing here was ever exercised.

That is how the argument swap below survived: `handle_check_suite` called
`_check_typescript(spec_path_obj, baseline, candidate)` against a signature of
`(candidate_code, baseline_code, spec_path)`, so the candidate slot received the spec
path and the actual test code was passed as a spec path.
"""

from __future__ import annotations

import pytest

from cherenkov.mcp.tools.core_cli import CORE_CLI_HANDLERS, handle_check_suite

_BASELINE_TS = """
test('get user', async () => {
  const { data } = await client.GET('/users/1');
  expect(data.total).toBe(10);
});
"""

_WEAKENED_TS = """
test('get user', async () => {
  const { data } = await client.GET('/users/1');
  expect(data.total).toBeGreaterThan(5);
});
"""


def test_all_three_tools_are_registered():
    assert set(CORE_CLI_HANDLERS) == {
        "cherenkov/check-suite",
        "cherenkov/verify",
        "cherenkov/generate",
    }


def test_missing_candidate_is_an_error():
    result = handle_check_suite({})
    assert "error" in result
    assert result["verdict"] == "fail"


def test_unchanged_typescript_suite_is_clean():
    """The case that pins the argument order.

    With the arguments swapped, the candidate slot got `spec_path_obj` — None here —
    so `_ts_parse_suite(None)` yielded an empty suite and every test present in the
    baseline was reported as `DELETED test removed entirely`. An unmodified suite came
    back dirty.
    """
    result = handle_check_suite(
        {"candidate_inline": _BASELINE_TS, "baseline_inline": _BASELINE_TS}
    )
    assert result["findings"] == [], result["findings"]
    assert result["verdict"] == "pass"


def test_weakened_typescript_assertion_is_reported_as_weakened():
    """A loosened matcher must be classed WEAKENED, not DELETED.

    Swapped arguments produced a DELETED finding for this input — the right verdict by
    accident, for entirely the wrong reason, since the candidate was never read.
    Asserting on the finding's *class* is what separates the two.
    """
    result = handle_check_suite(
        {"candidate_inline": _WEAKENED_TS, "baseline_inline": _BASELINE_TS}
    )
    assert result["findings"], "a weakened assertion must produce a finding"
    assert any("WEAKENED" in f for f in result["findings"]), result["findings"]
    assert not any("test removed entirely" in f for f in result["findings"]), result["findings"]
    assert result["verdict"] == "weakened"


def test_fail_on_finding_flips_the_verdict():
    result = handle_check_suite(
        {
            "candidate_inline": _WEAKENED_TS,
            "baseline_inline": _BASELINE_TS,
            "fail_on_finding": True,
        }
    )
    assert result["verdict"] == "fail"


@pytest.mark.parametrize("missing_baseline", [None, ""])
def test_typescript_without_baseline_does_not_crash(missing_baseline):
    """No baseline means nothing to compare against — not an exception."""
    params = {"candidate_inline": _BASELINE_TS}
    if missing_baseline is not None:
        params["baseline_inline"] = missing_baseline
    result = handle_check_suite(params)
    assert result["verdict"] in {"pass", "weakened", "fail"}
