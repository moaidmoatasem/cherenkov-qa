#!/usr/bin/env python3
"""
Standalone verification script for CherenkovTool import, instantiation, and capabilities.
"""

import sys
from typing import Any

def main() -> int:
    """Run standalone verification for CherenkovTool LangChain integration.

    Returns:
        Exit code integer (0 if all verifications pass, 1 otherwise).
    """
    print("=== Standalone CherenkovTool Verification ===")
    
    # 1. Test clean imports
    try:
        from cherenkov.langchain import (
            CherenkovTool,
            CherenkovGenerateTestsTool,
            CherenkovValidateTargetTool,
            CherenkovExplainViolationTool,
            CherenkovValidateTool,
            CherenkovToolkit,
        )
        from cherenkov.langchain.tool import CherenkovTool as DirectCherenkovTool
        from cherenkov.ai.langchain import CherenkovTool as AICherenkovTool
        print("[PASS] Clean import of CherenkovTool and all related LangChain classes.")
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return 1

    # 2. Test instantiation
    try:
        tool = CherenkovTool()
        assert tool.name == "cherenkov_qa", f"Expected name 'cherenkov_qa', got {tool.name}"
        assert tool.description, "Expected non-empty description"
        print("[PASS] CherenkovTool instantiated successfully.")
    except Exception as e:
        print(f"[FAIL] Instantiation error: {e}")
        return 1

    # 3. Test generate_tests capability method
    try:
        res_gen = tool.generate_tests(spec_path="stub/openapi.yaml", target_url="http://localhost:8000")
        assert isinstance(res_gen, str) and "stub/openapi.yaml" in res_gen
        print("[PASS] CherenkovTool.generate_tests() returned valid response.")
    except Exception as e:
        print(f"[FAIL] generate_tests error: {e}")
        return 1

    # 4. Test validate capability method
    try:
        from unittest.mock import patch
        with patch("cherenkov.execution.validate.ValidationEngine.validate_suite", return_value={"passed": 5, "failed": 0, "drift_count": 0}):
            res_val = tool.validate(target_url="http://localhost:8000", workers=1)
        assert isinstance(res_val, str) and "Validation" in res_val
        print("[PASS] CherenkovTool.validate() returned valid response.")
    except Exception as e:
        print(f"[FAIL] validate error: {e}")
        return 1

    # 5. Test explain_violation capability method
    try:
        res_exp = tool.explain_violation("non-existent-id")
        assert isinstance(res_exp, str) and "not found" in res_exp
        print("[PASS] CherenkovTool.explain_violation() returned valid response.")
    except Exception as e:
        print(f"[FAIL] explain_violation error: {e}")
        return 1

    # 6. Test CherenkovToolkit
    try:
        toolkit = CherenkovToolkit()
        tools = toolkit.get_tools()
        assert len(tools) == 5, f"Expected 5 tools in toolkit, got {len(tools)}"
        print("[PASS] CherenkovToolkit.get_tools() returned 5 tools.")
    except Exception as e:
        print(f"[FAIL] Toolkit error: {e}")
        return 1

    print("=== All CherenkovTool standalone verifications PASSED! ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
