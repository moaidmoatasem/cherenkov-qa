#!/usr/bin/env python3
"""Regenerate the MCP registry artifacts (`manifest.json`, `mcp.json`) from
`cherenkov/mcp/handlers.py` `TOOLS` so the shipped tool list can't drift.

The manifests are the single source of truth for the registries and are meant
to mirror `handlers.TOOLS` exactly (docs/README-MCP-PUBLISH.md). The drift-check
test `tests/unit/test_manifest_matches_tools.py` fails the build when they
diverge; running this script is the one-command fix.

Only the `tools` array is overwritten (with full tool entries from `TOOLS`):
the surrounding registry metadata ($schema, id, name, capabilities, resources,
… and the fixed header fields in `mcp.json`) are preserved as committed.

Usage:
    python scripts/gen_manifest.py            # rewrite both files
    python scripts/gen_manifest.py --check    # fail if a rewrite is needed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = REPO_ROOT / "manifest.json"
MCP_JSON_PATH = REPO_ROOT / "mcp.json"


def _manifest_tools(tools) -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema.model_dump(),
        }
        for tool in tools
    ]


def _mcp_json_tools(tools) -> list[dict]:
    return [{"name": tool.name, "description": tool.description} for tool in tools]


def regenerate() -> tuple[dict, dict]:
    """Recompute both registry files' tools array from handlers.TOOLS."""
    from cherenkov.mcp.handlers import TOOLS

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mcp_json = json.loads(MCP_JSON_PATH.read_text(encoding="utf-8"))

    manifest["tools"] = _manifest_tools(TOOLS)
    mcp_json["tools"] = _mcp_json_tools(TOOLS)
    return manifest, mcp_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the manifests already match TOOLS; exit 1 if a regen is needed.",
    )
    args = parser.parse_args()

    manifest, mcp_json = regenerate()
    if args.check:
        current_m = MANIFEST_PATH.read_text(encoding="utf-8")
        current_mj = MCP_JSON_PATH.read_text(encoding="utf-8")
        new_m = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        new_mj = json.dumps(mcp_json, indent=2, ensure_ascii=False) + "\n"
        if current_m != new_m or current_mj != new_mj:
            print("DRIFT: manifests are out of sync with handlers.TOOLS.", file=sys.stderr)
            print("Run:  python scripts/gen_manifest.py", file=sys.stderr)
            return 1
        print("manifest.json and mcp.json match handlers.TOOLS")
        return 0

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MCP_JSON_PATH.write_text(json.dumps(mcp_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Regenerated {MANIFEST_PATH.relative_to(REPO_ROOT)} and {MCP_JSON_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())