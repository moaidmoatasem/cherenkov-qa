"""#1040: what `cherenkov init` scaffolds must be accepted by the rest of the tool."""
from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

from cherenkov.core.config_loader import KNOWN_KEYS
from cherenkov.stages.init_cmd import generate_github_actions_workflow, generate_toml

ROOT = Path(__file__).resolve().parents[2]


def _flatten(d: dict, prefix: str = "") -> list[str]:
    out: list[str] = []
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and not any(key.startswith(n) and key != n for n in ()):
            out += _flatten(v, f"{key}.")
        else:
            out.append(key)
    return out


def test_every_key_init_writes_is_known_to_the_loader():
    data = tomllib.loads(generate_toml(["openapi.yaml"], "laptop", "CPU"))
    unknown = [k for k in _flatten(data) if k not in KNOWN_KEYS]
    assert unknown == []


def test_scaffolded_workflow_uses_real_action_inputs():
    wf = yaml.safe_load(generate_github_actions_workflow())
    step = next(s for s in wf["jobs"]["integrity"]["steps"] if "cherenkov" in s.get("uses", ""))
    declared = set(yaml.safe_load((ROOT / "action.yml").read_text())["inputs"])
    assert set(step["with"]) <= declared
    assert "cherenkov-qa/action@v1" not in step["uses"]
