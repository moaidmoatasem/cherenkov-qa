from unittest.mock import patch
from cherenkov.core.orchestrator import OrchestrationEngine


@patch("cherenkov.core.settings.CherenkovSettings.detect_ollama_device", return_value="cpu")
def test_validation_mutation(mock_detect):
    # We simulate a pipeline run that fails during GENERATE or REVIEW
    engine = OrchestrationEngine(run_id="mut_val")

    # Test that simulate_fail_stage triggers the circuit breaker or fails the pipeline
    success = engine.run_pipeline("mut_spec.json", simulate_fail_stage="REVIEW")

    assert (
        not success
    ), "Pipeline should fail when REVIEW stage is deliberately mutated to fail."
