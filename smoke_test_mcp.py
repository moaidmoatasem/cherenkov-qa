"""
smoke_test_mcp.py — Kill-criteria exit demo for the CHERENKOV MCP server (mcp/v1).

Kill criteria (all must pass for exit 0):
  1. MCP server handles `initialize` handshake — correct protocolVersion + capabilities shape
  2. `tools/list` returns all 4 required tools (hitl_list, hitl_approve, hitl_reject, validate_run_gate)
  3. `resources/list` returns all 4 required resources (cherenkov://hitl/pending, ...)
  4. `hitl_list` tool returns a valid hitl/v1 envelope shape (empty queue is ok)
  5. Invalid `item_id` (empty string) is rejected before reaching HitlQueue — isError=True
  6. Malformed JSON-RPC is handled gracefully — parse error code returned, no crash
  7. `cherenkov mcp serve --help` listed in CLI help (docs gate)

Runs entirely in-process using stream injection — no real MCP client needed.
D7 honored: zero test files touched.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys

PASS = "  [ok]"
FAIL = "  [FAIL]"
_failures = []


def _rpc(table, method: str, params: dict, req_id=1) -> dict:
    from cherenkov.mcp.protocol import dispatch_one
    raw = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
    resp = dispatch_one(raw, table)
    assert resp is not None, f"No response for method {method!r}"
    return json.loads(resp.model_dump_json())


def check(label: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"{PASS} {label}")
    else:
        msg = f"{FAIL} {label}" + (f"\n       detail: {detail}" if detail else "")
        print(msg)
        _failures.append(label)


def run() -> None:
    from cherenkov.mcp.server import build_dispatch_table

    print("=" * 60)
    print("  CHERENKOV MCP Smoke Test — kill-criteria exit demo")
    print("=" * 60)

    table = build_dispatch_table()

    # ── Kill criterion 1: initialize handshake ────────────────────────────────
    resp = _rpc(table, "initialize", {"protocolVersion": "2024-11-05", "clientInfo": {}})
    check("initialize: no JSON-RPC error", resp.get("error") is None)
    result = resp.get("result", {})
    check(
        "initialize: protocolVersion = '2024-11-05'",
        result.get("protocolVersion") == "2024-11-05",
        str(result.get("protocolVersion")),
    )
    check(
        "initialize: serverInfo.name = 'cherenkov'",
        result.get("serverInfo", {}).get("name") == "cherenkov",
    )
    check(
        "initialize: capabilities has resources + tools",
        "resources" in result.get("capabilities", {}) and "tools" in result.get("capabilities", {}),
        str(result.get("capabilities")),
    )

    # ── Kill criterion 2: tools/list — 4 required tools ──────────────────────
    resp = _rpc(table, "tools/list", {})
    check("tools/list: no error", resp.get("error") is None)
    tools_by_name = {t["name"]: t for t in resp.get("result", {}).get("tools", [])}
    for required in ("hitl_list", "hitl_approve", "hitl_reject", "validate_run_gate"):
        check(f"tools/list: '{required}' present", required in tools_by_name)
        if required in tools_by_name:
            schema = tools_by_name[required].get("inputSchema", {})
            check(f"tools/list: '{required}' has inputSchema", schema.get("type") == "object")

    # ── Kill criterion 3: resources/list — 4 required resources ──────────────
    resp = _rpc(table, "resources/list", {})
    check("resources/list: no error", resp.get("error") is None)
    resources = resp.get("result", {}).get("resources", [])
    uris = {r["uri"] for r in resources}
    for required_uri in (
        "cherenkov://hitl/pending",
        "cherenkov://hitl/item/{id}",
        "cherenkov://validate/latest",
        "cherenkov://validate/evidence",
    ):
        check(f"resources/list: '{required_uri}' present", required_uri in uris)

    # ── Kill criterion 4: hitl_list returns hitl/v1 envelope ─────────────────
    resp = _rpc(table, "tools/call", {"name": "hitl_list", "arguments": {"status": "pending"}})
    check("tools/call hitl_list: no JSON-RPC error", resp.get("error") is None)
    tool_result = resp.get("result", {})
    check("tools/call hitl_list: not isError", not tool_result.get("isError", True))
    content_text = (tool_result.get("content") or [{}])[0].get("text", "{}")
    try:
        payload = json.loads(content_text)
        check("tools/call hitl_list: schema_version = 'hitl/v1'",
              payload.get("schema_version") == "hitl/v1",
              str(payload.get("schema_version")))
        check("tools/call hitl_list: ok = True", payload.get("ok") is True)
        check("tools/call hitl_list: payload is list", isinstance(payload.get("payload"), list))
    except Exception as exc:
        check("tools/call hitl_list: parseable JSON content", False, str(exc))

    # ── Kill criterion 5: invalid item_id rejected at trust boundary ──────────
    resp = _rpc(table, "tools/call", {"name": "hitl_approve", "arguments": {"item_id": ""}})
    check("trust boundary: empty item_id → no JSON-RPC crash", resp.get("error") is None)
    tool_result = resp.get("result", {})
    check(
        "trust boundary: empty item_id → isError=True",
        tool_result.get("isError", False) is True,
        str(tool_result),
    )

    # ── Kill criterion 6: malformed JSON-RPC → parse error, no crash ─────────
    from cherenkov.mcp.protocol import dispatch_one
    bad_resp = dispatch_one("{{not valid json}}", table)
    check("malformed JSON: no crash", bad_resp is not None)
    from cherenkov.mcp.contracts import PARSE_ERROR
    check(
        "malformed JSON: error.code = PARSE_ERROR",
        bad_resp is not None and bad_resp.error is not None and bad_resp.error.code == PARSE_ERROR,
        str(bad_resp.error.code if bad_resp and bad_resp.error else "None"),
    )

    # ── Kill criterion 7: docs gate — `mcp` listed in CLI help ───────────────
    result = subprocess.run(
        [sys.executable, "cherenkov.py", "--help"],
        capture_output=True, text=True, timeout=15
    )
    check(
        "docs gate: 'mcp' listed in `cherenkov --help`",
        "mcp" in result.stdout,
        result.stdout[:300],
    )

    # ── stdio transport round-trip ────────────────────────────────────────────
    from cherenkov.mcp.protocol import serve_stdio
    two_pings = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}),
    ]) + "\n"
    inp = io.StringIO(two_pings)
    out = io.StringIO()
    serve_stdio(table, input_stream=inp, output_stream=out)
    lines = [l for l in out.getvalue().splitlines() if l.strip()]
    check("stdio transport: 2 ping requests → 2 responses", len(lines) == 2, str(len(lines)))
    ids_seen = {json.loads(l)["id"] for l in lines}
    check("stdio transport: response IDs match request IDs", ids_seen == {1, 2}, str(ids_seen))

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if _failures:
        print(f"[FAIL] {len(_failures)} kill criteria NOT met:")
        for f in _failures:
            print(f"  - {f}")
        print("\nMCP smoke: FAILED")
        sys.exit(1)
    else:
        print("=" * 60)
        print("  ALL MCP KILL CRITERIA MET — mcp/v1 server is ready.")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    run()
