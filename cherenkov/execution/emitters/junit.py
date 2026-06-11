from __future__ import annotations

import xml.etree.ElementTree as ET
import xml.dom.minidom
from typing import Any, Dict

def emit_junit(results: Dict[str, Any], spec_path: str | None = None) -> str:
    """Generates a valid JUnit XML representation of the validation results."""
    reports = results.get("reports", [])
    
    # Group reports by endpoint: (method, endpoint)
    grouped: Dict[str, list[Dict[str, Any]]] = {}
    for r in reports:
        method = r.get("method") or "UNKNOWN"
        endpoint = r.get("endpoint") or "unknown"
        key = f"{method} {endpoint}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)
        
    testsuites = ET.Element("testsuites", name="CHERENKOV Validation")
    
    total_tests = 0
    total_failures = 0
    
    for key, scen_list in grouped.items():
        suite_tests = len(scen_list)
        suite_failures = sum(1 for r in scen_list if not r.get("passed", False))
        
        total_tests += suite_tests
        total_failures += suite_failures
        
        testsuite = ET.SubElement(
            testsuites, 
            "testsuite", 
            name=key, 
            tests=str(suite_tests), 
            failures=str(suite_failures),
            errors="0"
        )
        
        for r in scen_list:
            scenario_id = r.get("scenario_id", "unknown")
            passed = r.get("passed", False)
            
            testcase = ET.SubElement(
                testsuite,
                "testcase",
                name=scenario_id,
                classname=key
            )
            
            if not passed:
                err_msg = r.get("error") or "Validation failed"
                failure = ET.SubElement(
                    testcase,
                    "failure",
                    message=err_msg,
                    type="AssertionError"
                )
                failure.text = err_msg
                
    testsuites.set("tests", str(total_tests))
    testsuites.set("failures", str(total_failures))
    testsuites.set("errors", "0")
    
    # Return pretty-printed XML string
    rough_str = ET.tostring(testsuites, "utf-8")
    reparsed = xml.dom.minidom.parseString(rough_str)
    return reparsed.toprettyxml(indent="  ")
