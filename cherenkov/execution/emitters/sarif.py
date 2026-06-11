from __future__ import annotations

import json
import os
from typing import Any, Dict, List

def emit_sarif(results: Dict[str, Any], spec_path: str | None = None) -> str:
    """Generates a valid SARIF 2.1.0 representation of the validation results."""
    reports = results.get("reports", [])
    
    # Default spec path if not specified
    if not spec_path:
        spec_path = "stub/target_spec.json"
        
    rules_map: Dict[str, Dict[str, Any]] = {}
    sarif_results: List[Dict[str, Any]] = []
    
    # Lazy import to avoid circular dependency
    from cherenkov.execution.validate import find_spec_line
    
    for r in reports:
        if r.get("passed", False):
            continue
            
        method = r.get("method") or "UNKNOWN"
        endpoint = r.get("endpoint") or "unknown"
        rule_id = f"{method} {endpoint}"
        
        if rule_id not in rules_map:
            rules_map[rule_id] = {
                "id": rule_id,
                "shortDescription": {
                    "text": f"Conformance validation for {rule_id}"
                }
            }
            
        err_msg = r.get("error") or "Validation failed"
        
        # Get line number of the endpoint/method in the spec file
        spec_line = find_spec_line(spec_path, method, endpoint)
        
        # Make spec path relative to project root for standard SARIF output
        rel_spec_path = os.path.relpath(spec_path, os.getcwd()).replace("\\", "/") if os.path.isabs(spec_path) else spec_path
        
        result_obj = {
            "ruleId": rule_id,
            "message": {
                "text": err_msg
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": rel_spec_path
                        },
                        "region": {
                            "startLine": spec_line
                        }
                    }
                }
            ]
        }
        sarif_results.append(result_obj)
        
    rules = list(rules_map.values())
    
    sarif_log = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
          {
            "tool": {
              "driver": {
                "name": "CHERENKOV-QA",
                "version": "1.0.0",
                "informationUri": "https://github.com/moaidmoatasem/cherenkov-qa",
                "rules": rules
              }
            },
            "results": sarif_results
          }
        ]
    }
    
    return json.dumps(sarif_log, indent=2)
