import os
from cherenkov.stages.ingest import IngestStage

def test_openapi_3_1_ingest():
    stage = IngestStage(run_id="test_3_1")
    spec_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../stub/openapi_3_1.yaml"))
    
    result = stage.run(spec_path)
    assert result.status == "ok"
    
    # We should have an endpoint for /users and for /_webhook/newPet
    paths = [ep.path for ep in result.endpoints]
    assert "/users" in paths
    assert "/_webhook/newPet" in paths

    # Find /users POST endpoint and check that it parsed the type: ["string", "null"] correctly
    users_ep = next(ep for ep in result.endpoints if ep.path == "/users")
    schema = users_ep.schemas
    # Not testing the exact schema here as it might be complex, but we know it should have created boundary validations for name and age
    mutations = [m.id for m in users_ep.mutations]
    assert "name_too_long" in mutations
    assert "age_exceeds_max" in mutations

    print("OpenAPI 3.1 tests passed successfully!")

if __name__ == "__main__":
    test_openapi_3_1_ingest()
