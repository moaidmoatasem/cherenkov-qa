import json
import os
import pytest
from cherenkov.enterprise import (
    get_org_manager,
    get_audit_log,
    get_soc2,
)


@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup
    manager = get_org_manager()
    manager._orgs.clear()

    yield

    # Teardown
    if os.path.exists(".cherenkov/audit/audit.jsonl"):
        os.remove(".cherenkov/audit/audit.jsonl")


def test_org_manager_creates_org():
    manager = get_org_manager()
    org = manager.create_org(name="Acme Corp", owner_id="user_123")
    
    assert org.name == "Acme Corp"
    assert org.owner_id == "user_123"
    assert len(org.members) == 1
    assert org.members[0].user_id == "user_123"
    assert org.members[0].role == "owner"


def test_org_manager_teams_and_projects():
    manager = get_org_manager()
    org = manager.create_org(name="Global Tech", owner_id="user_admin")
    
    team = manager.create_team(org.id, "Backend Devs")
    project = manager.create_project(org.id, "API v2")
    
    assert team is not None
    assert project is not None
    assert team.name == "Backend Devs"
    assert project.name == "API v2"


def test_audit_log_records_and_exports(tmp_path):
    audit = get_audit_log()
    
    # Use tmp_path to isolate test logs
    audit.storage_dir = tmp_path
    audit.current_log_file = tmp_path / "test_audit.jsonl"
    
    audit.log_event("user_123", "delete_resource", "doc_456", {"reason": "GDPR right to be forgotten"})
    audit.log_event("user_456", "login", "auth_system")
    
    json_export_path = tmp_path / "audit_export.json"
    audit.export_json(str(json_export_path))
    
    with open(json_export_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert len(data) == 2
    assert data[0]["actor"] == "user_123"
    assert data[0]["action"] == "delete_resource"
    assert data[0]["details"]["reason"] == "GDPR right to be forgotten"


def test_soc2_generator_exports_json():
    generator = get_soc2()
    report = generator.generate_report("Acme")
    
    # Needs to be serialized, as it returns an object
    data = report.__dict__
    assert data["organization"] == "Acme"
    assert data["status"] == "draft"
    assert "controls" in data
    assert len(data["controls"]) > 0
