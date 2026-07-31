import json
import sys
from cherenkov.execution.emitters.sarif import SARIFEmitter

# Test 1: Unit verification of SARIFEmitter output schema
class MockFinding:
    def __init__(self, violation_type, severity, summary, endpoint, http_method, expected, actual):
        self.violation_type = violation_type
        self.severity = severity
        self.summary = summary
        self.endpoint = endpoint
        self.http_method = http_method
        self.expected = expected
        self.actual = actual
        self.description = "Test drift description"
        self.remediation = "Fix API implementation"

class MockReport:
    def __init__(self, findings):
        self.findings = findings

findings = [
    MockFinding("status_mismatch", "high", "Expected HTTP 200, got 500", "/pets", "GET", "200", "500"),
    MockFinding("schema_drift", "medium", "Missing field 'name'", "/pets/1", "GET", "present", "missing")
]

report = MockReport(findings)
emitter = SARIFEmitter()
sarif_dict = emitter.emit(report, "docs/openapi-demo.yaml")

print("[SARIF Unit Test] Generated SARIF output:")
print(json.dumps(sarif_dict, indent=2))

# Verify SARIF v2.1.0 mandatory fields
assert sarif_dict.get("$schema") == "https://json.schemastore.org/sarif-2.1.0.json", "Invalid $schema"
assert sarif_dict.get("version") == "2.1.0", "Invalid version"
assert len(sarif_dict.get("runs", [])) > 0, "Missing runs array"

driver = sarif_dict["runs"][0]["tool"]["driver"]
assert driver["name"] == "Cherenkov QA", "Invalid driver name"

results = sarif_dict["runs"][0]["results"]
assert len(results) == 2, f"Expected 2 results, got {len(results)}"
assert results[0]["ruleId"] == "status_mismatch", "Invalid ruleId"
assert results[0]["level"] == "error", "Invalid level for high severity"
assert results[1]["level"] == "warning", "Invalid level for medium severity"
assert results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "docs/openapi-demo.yaml"

print("\nSUCCESS: SARIF v2.1.0 schema verification passed!")
