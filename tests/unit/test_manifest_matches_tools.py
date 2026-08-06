"""tests/unit/test_manifest_matches_tools.py — registry manifests ↔ TOOLS drift.

`manifest.json` and `mcp.json` are the MCP registry artifacts. They are meant to
mirror `cherenkov/mcp/handlers.py` `TOOLS` exactly — same tools, same order
(docs/README-MCP-PUBLISH.md calls the manifest "the single source of truth …
extracted programmatically from TOOLS"). Nothing enforced that, and four
`event_bus_*` tools escaped the manifests until #918 regenerated them.

This test makes a 37→41-style drift un-mergeable: name + order must match for
both registry artifacts. The optional `scripts/gen_manifest.py` script
regenerates both from `TOOLS` to fix a failure in one command.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cherenkov.mcp.handlers import TOOLS

REPO_ROOT = Path(__file__).resolve().parents[2]

_MANIFEST = REPO_ROOT / "manifest.json"
_MCP_JSON = REPO_ROOT / "mcp.json"

_EXPECTED_TOOL_NAMES = [tool.name for tool in TOOLS]


@pytest.mark.parametrize("artifact", [_MANIFEST, _MCP_JSON])
def test_registry_artifact_matches_handlers_tools_name_and_order(artifact: Path):
    data = json.loads(artifact.read_text(encoding="utf-8"))
    shipped_names = [entry["name"] for entry in data["tools"]]
    assert shipped_names == _EXPECTED_TOOL_NAMES, (
        f"{artifact.name} drift: manifests ship {len(shipped_names)} tools "
        "(in dependency order), handlers.TOOLS declares "
        f"{len(_EXPECTED_TOOL_NAMES)}. Regenerate with `python "
        "scripts/gen_manifest.py` (or sync the artifact) before merging."
    )


def test_both_artifacts_are_in_sync_with_each_other():
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    mcp_json = json.loads(_MCP_JSON.read_text(encoding="utf-8"))
    assert [t["name"] for t in manifest["tools"]] == [
        t["name"] for t in mcp_json["tools"]
    ]