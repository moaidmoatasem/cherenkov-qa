"""Every environment variable `action.yml` sets must be one the package reads.

`action.yml` is the primary distribution surface (M3, "one surface"), and an
env-var name that nothing reads fails *silently*: the run succeeds, the setting
is ignored, and the user sees a result produced by defaults they never chose.

This is a known drift class in this repository, not a hypothetical. Round 3
(`156dba0`) replaced `CHERENKOV_LLM_PROVIDER` / `CHERENKOV_LLM_MODEL` throughout
`docs/wiki/` because those names exist nowhere in `cherenkov/core/settings.py` —
but that sweep never reached `action.yml`, which went on setting them. The
Action's documented `llm-provider: openai` default therefore ran against Ollama.

Same bug shape as #726's doctor fix landing in the web onboarding wizard but not
the CLI's own doctor: the fix reached the docs and missed the code.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION_YML = REPO_ROOT / "action.yml"
SETTINGS_PY = REPO_ROOT / "cherenkov" / "core" / "settings.py"

# Names supplied by the runner or the user's workflow, not read through settings.
_RUNNER_PROVIDED = {"GITHUB_OUTPUT", "GITHUB_ENV", "GITHUB_TOKEN", "PATH"}


def _settings_aliases() -> set[str]:
    source = SETTINGS_PY.read_text(encoding="utf-8")
    aliases = set(re.findall(r"validation_alias=['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", source))
    # Fields declared without an explicit alias are read under their own name.
    aliases |= set(re.findall(r"^\s{4}([A-Z][A-Z0-9_]*)\s*:\s*\w", source, re.MULTILINE))
    return aliases


def _action_env_names() -> set[str]:
    action = yaml.safe_load(ACTION_YML.read_text(encoding="utf-8"))
    names: set[str] = set()
    for step in action["runs"]["steps"]:
        names |= set(step.get("env") or {})
    return names


def test_action_yml_parses():
    action = yaml.safe_load(ACTION_YML.read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "composite"
    assert action["runs"]["steps"], "action.yml declares no steps"


def test_settings_aliases_were_actually_found():
    """Fail loudly if the alias scrape breaks, rather than passing vacuously."""
    aliases = _settings_aliases()
    assert len(aliases) > 50, f"only found {len(aliases)} settings aliases — scrape is broken"
    assert {"PROVIDER", "GEN_MODEL", "OPENAI_API_KEY"} <= aliases


@pytest.mark.parametrize("name", sorted(_action_env_names()))
def test_every_action_env_var_is_read_by_settings(name: str):
    if name in _RUNNER_PROVIDED:
        pytest.skip(f"{name} is provided by the runner")
    assert name in _settings_aliases(), (
        f"action.yml sets {name}, which nothing in cherenkov/core/settings.py reads. "
        f"The Action would run with defaults and report success — a silent no-op."
    )


def test_the_two_names_that_regressed_are_gone():
    """Explicit regression guard for the exact names that were inert."""
    raw = ACTION_YML.read_text(encoding="utf-8")
    for dead in ("CHERENKOV_LLM_PROVIDER:", "CHERENKOV_LLM_MODEL:"):
        assert dead not in raw, f"{dead[:-1]} does not exist in settings.py; it is read by nothing"
