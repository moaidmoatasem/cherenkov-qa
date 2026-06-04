import unittest
from cherenkov.core.orchestrator import OrchestrationEngine

class TestMutationValidate(unittest.TestCase):
    def test_validation_mutation(self):
        # We simulate a pipeline run that fails during GENERATE or REVIEW
        engine = OrchestrationEngine(run_id="mut_val")
        
        # Test that simulate_fail_stage triggers the circuit breaker or fails the pipeline
        success = engine.run_pipeline("mut_spec.json", simulate_fail_stage="REVIEW")
        
        self.assertFalse(success, "Pipeline should fail when REVIEW stage is deliberately mutated to fail.")

if __name__ == "__main__":
    unittest.main()
