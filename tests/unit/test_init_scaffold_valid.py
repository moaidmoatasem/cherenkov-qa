"""#1040: what `cherenkov init` scaffolds must be accepted by the rest of the tool."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from cherenkov.core.config_loader import KNOWN_KEYS
from cherenkov.stages.init_cmd import generate_github_actions_workflow, generate_toml

ROOT = Path(__file__).resolve().parents[2]


def _written_keys(toml_text: str) -> list[str]:
    """Dotted `section.key` names in init's TOML.

    Hand-parsed on purpose: `tomllib` is 3.11+ and `tomli` is not a declared
    dependency, so CI on 3.10 could not import either. The template only uses
    `[table]` headers and single-line `key = value` pairs.
    """
    keys: list[str] = []
    section = ""
    for line in toml_text.splitlines():
        header = re.match(r"^\[([\w.]+)\]\s*(#.*)?$", line)
        if header:
            section = header.group(1)
            continue
        pair = re.match(r"^([A-Za-z_]\w*)\s*=", line)
        if pair:
            keys.append(f"{section}.{pair.group(1)}" if section else pair.group(1))
    return keys


def test_every_key_init_writes_is_known_to_the_loader():
    keys = _written_keys(generate_toml(["openapi.yaml"], "laptop", "CPU"))
    assert keys, "parser found no keys; the template format changed"
    unknown = [k for k in keys if k not in KNOWN_KEYS]
    assert unknown == []


def test_scaffolded_workflow_uses_real_action_inputs():
    wf = yaml.safe_load(generate_github_actions_workflow())
    step = next(s for s in wf["jobs"]["integrity"]["steps"] if "cherenkov" in s.get("uses", ""))
    declared = set(yaml.safe_load((ROOT / "action.yml").read_text())["inputs"])
    assert set(step["with"]) <= declared
    assert "cherenkov-qa/action@v1" not in step["uses"]
