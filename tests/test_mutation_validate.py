import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cherenkov.core.orchestrator import OrchestrationEngine

_FIXTURE_SPEC = str(Path(__file__).parent / "fixtures" / "mut_spec.json")


@patch.dict(os.environ, {"CHERENKOV_ENV": "development"})
@patch("cherenkov.core.settings.CherenkovSettings.detect_ollama_device", return_value="cpu")
def test_validation_mutation(mock_detect):
    # We simulate a pipeline run that fails during GENERATE or REVIEW
    engine = OrchestrationEngine(run_id="mut_val")

    # Test that simulate_fail_stage triggers the circuit breaker or fails the pipeline
    success = engine.run_pipeline(_FIXTURE_SPEC, simulate_fail_stage="REVIEW")

    assert (
        not success
    ), "Pipeline should fail when REVIEW stage is deliberately mutated to fail."
