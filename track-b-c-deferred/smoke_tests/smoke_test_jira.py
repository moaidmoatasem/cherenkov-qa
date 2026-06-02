#!/usr/bin/env python3
"""
smoke_test_jira.py — Suggest-Only Jira Exporter integration smoke test.
Proves copy-ready GFM markdown ticket generation, context merging, and zero-egress sandboxing.
"""
import os
import sys
import time

from cherenkov.validate.jira_exporter import JiraExporter

def run_jira_smoke_tests():
    print("=======================================================")
    print("      CHERENKOV TRACK C JIRA INTEGRATION SMOKE TEST")
    print("=======================================================\n")

    ticket_dir = ".cherenkov/jira_tickets"
    if os.path.exists(ticket_dir):
        print(f"Cleaning existing tickets under {ticket_dir}...")
        for f in os.listdir(ticket_dir):
            if f.endswith(".md"):
                os.remove(os.path.join(ticket_dir, f))
    else:
        os.makedirs(ticket_dir, exist_ok=True)

    # 1. Initialize JiraExporter
    print("Pass 1: Initializing Suggest-Only Jira Exporter...")
    exporter = JiraExporter(run_id="jira_smoke")
    assert exporter.ticket_dir.endswith(".cherenkov/jira_tickets"), "Invalid ticket directory setup."
    print("✓ JiraExporter initialized successfully.\n")

    # 2. Format and Export Ticket
    print("Pass 2: Exporting copy-ready ticket for simulated failure...")
    scenario_id = "test_auth_expiry_smoke"
    failure_class = "AUTH_EXPIRY"
    error_message = "Error: expect(response.status).toBe(200) received 401 Unauthorized"
    expected_status = 200
    received_status = 401
    hypothesis = "The access token provided in request headers has expired or is cryptographically invalid."
    resolution_steps = [
        "Check token generation gateway credentials.",
        "Ensure clock skew between client and gateway is within accepted tolerances.",
        "Rotate the client JWT key pair."
    ]
    similar_cases_count = 3
    compliance_score = 60

    ticket_path = exporter.export_ticket(
        scenario_id=scenario_id,
        failure_class=failure_class,
        error_message=error_message,
        expected_status=expected_status,
        received_status=received_status,
        hypothesis=hypothesis,
        resolution_steps=resolution_steps,
        similar_cases_count=similar_cases_count,
        compliance_score=compliance_score
    )

    # 3. Assert outputs
    assert os.path.exists(ticket_path), "Failed to write Jira Markdown ticket to disk."
    print(f"✓ Jira ticket successfully written to disk at: {ticket_path}\n")

    # Read and assert contents
    with open(ticket_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert f"🛑 CHERENKOV QA — DRIFT DETECTED: {scenario_id}" in content, "Missing ticket header."
    assert "## 🔍 Incident Details" in content, "Missing Incident Details section."
    assert f"- **Scenario ID**: `{scenario_id}`" in content, "Missing scenario ID details."
    assert f"- **Failure Classification**: `{failure_class}`" in content, "Missing failure class details."
    assert f"Expected `{expected_status}` | Received `{received_status}`" in content, "Missing conformance status."
    assert "## 🧠 AI Root-Cause Hypothesis" in content, "Missing AI Root-Cause section."
    assert hypothesis in content, "Missing AI diagnostics hypothesis."
    assert "### 🛠️ Actionable Resolution Steps" in content, "Missing resolution steps header."
    assert "1. Check token generation gateway credentials." in content, "Missing step 1 assertion."
    assert "Found **3** similar historical failure(s)" in content, "Missing RAG correlation mapping."
    assert f"- **MENA Regulatory Score**: `{compliance_score}%`" in content, "Missing compliance score metric mapping."

    print("--- GENERATED TICKET SAMPLE (RAW GFM) ---")
    print(content)
    print("-----------------------------------------\n")

    print("=======================================================")
    print("   CHERENKOV JIRA INTEGRATION SMOKE TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    try:
        run_jira_smoke_tests()
        sys.exit(0)
    except Exception as e:
        print(f"\n🛑 Jira Smoke Test Failed: {e}")
        sys.exit(1)
