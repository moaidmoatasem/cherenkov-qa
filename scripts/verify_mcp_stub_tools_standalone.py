#!/usr/bin/env python3
"""
Standalone verification script for MCP server tools:
- export_jira_ticket
- run_k6_perf
- scan_mena_compliance
"""

import json
import sys
from typing import Any

def main() -> int:
    """Run standalone verification for MCP server tools.

    Returns:
        Exit code integer (0 if all tool checks pass, 1 otherwise).
    """
    print("=== Standalone MCP Tools Verification ===")

    try:
        from cherenkov.mcp.protocol import dispatch_one
        from cherenkov.mcp.server import build_dispatch_table
        table = build_dispatch_table()
        print("[PASS] MCP server dispatch table built successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to build MCP dispatch table: {e}")
        return 1

    # 1. Verify tools/list contains the 3 tools
    try:
        req_list = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        resp_list = dispatch_one(req_list, table)
        assert resp_list and resp_list.result, "tools/list returned empty result"
        tool_names = {t["name"] for t in resp_list.result.get("tools", [])}
        
        required_tools = ["export_jira_ticket", "run_k6_perf", "scan_mena_compliance"]
        for tool_name in required_tools:
            assert tool_name in tool_names, f"Tool '{tool_name}' missing from tools/list catalogue!"
        print(f"[PASS] tools/list exposes all 3 required tools: {required_tools}")
    except Exception as e:
        print(f"[FAIL] tools/list check failed: {e}")
        return 1

    # 2. Test export_jira_ticket
    try:
        req_jira = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "export_jira_ticket",
                "arguments": {
                    "summary": "Standalone Verification Jira Ticket",
                    "description": "Verification description for direct Jira export.",
                    "project_key": "QA",
                    "sandbox_only": True
                }
            }
        })
        resp_jira = dispatch_one(req_jira, table)
        assert resp_jira and resp_jira.result, "export_jira_ticket returned no result"
        assert not resp_jira.result.get("isError", False), f"export_jira_ticket returned error: {resp_jira.result}"
        
        content_text = resp_jira.result["content"][0]["text"]
        payload = json.loads(content_text)
        assert isinstance(payload, dict), f"Expected dict payload, got {type(payload)}"
        assert payload.get("status") == "exported", f"Expected status 'exported', got {payload.get('status')}"
        assert "file_path" in payload and payload["file_path"], "file_path missing or empty in payload"
        assert payload.get("jira_issue_key") == "sandboxed", f"Expected sandboxed key, got {payload.get('jira_issue_key')}"
        print(f"[PASS] export_jira_ticket returned valid structured response:\n  File: {payload['file_path']}\n  Status: {payload['status']}")
    except Exception as e:
        print(f"[FAIL] export_jira_ticket verification failed: {e}")
        return 1

    # 3. Test run_k6_perf
    try:
        req_k6 = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "run_k6_perf",
                "arguments": {
                    "target_url": "http://localhost:8000",
                    "scenario_name": "soak_test",
                    "duration": "3s",
                    "vus": 2
                }
            }
        })
        resp_k6 = dispatch_one(req_k6, table)
        assert resp_k6 and resp_k6.result, "run_k6_perf returned no result"
        assert not resp_k6.result.get("isError", False), f"run_k6_perf returned error: {resp_k6.result}"
        
        content_text = resp_k6.result["content"][0]["text"]
        payload = json.loads(content_text)
        assert isinstance(payload, dict), f"Expected dict payload, got {type(payload)}"
        assert "scenario_id" in payload, "scenario_id missing in k6 response"
        assert "status" in payload, "status missing in k6 response"
        assert "verdict" in payload, "verdict missing in k6 response"
        assert "gates" in payload, "gates missing in k6 response"
        print(f"[PASS] run_k6_perf returned valid structured response:\n  Scenario ID: {payload['scenario_id']}\n  Status: {payload['status']}\n  Verdict: {payload['verdict']}")
    except Exception as e:
        print(f"[FAIL] run_k6_perf verification failed: {e}")
        return 1

    # 4. Test scan_mena_compliance
    try:
        req_mena = json.dumps({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "scan_mena_compliance",
                "arguments": {
                    "target_url": "http://localhost:8000",
                    "spec_path": "stub/openapi.yaml"
                }
            }
        })
        resp_mena = dispatch_one(req_mena, table)
        assert resp_mena and resp_mena.result, "scan_mena_compliance returned no result"
        assert not resp_mena.result.get("isError", False), f"scan_mena_compliance returned error: {resp_mena.result}"
        
        content_text = resp_mena.result["content"][0]["text"]
        payload = json.loads(content_text)
        assert isinstance(payload, dict), f"Expected dict payload, got {type(payload)}"
        assert "compliance_score" in payload, "compliance_score missing in MENA response"
        assert "violations" in payload, "violations missing in MENA response"
        assert "mappings" in payload or "sama_ccsf" in payload, "mappings/sama_ccsf missing in MENA response"
        assert "audit_results" in payload, "audit_results missing in MENA response"
        print(f"[PASS] scan_mena_compliance returned valid structured response:\n  Score: {payload['compliance_score']}%\n  Violations count: {len(payload['violations'])}")
    except Exception as e:
        print(f"[FAIL] scan_mena_compliance verification failed: {e}")
        return 1

    print("=== All MCP tool structured response verifications PASSED! ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
