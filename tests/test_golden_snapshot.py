# TODO: convert to pytest — integration test with mocks heavily (left for follow-up)
import unittest
from unittest.mock import patch, MagicMock
from cherenkov.stages.generate import GenerateStage
from cherenkov.core.contracts import Scenario


class TestGoldenSnapshot(unittest.TestCase):
    @patch("cherenkov.stages.generate.get_client")
    @patch("cherenkov.cache.endpoint_cache.EndpointCache")
    def test_golden_generation(self, mock_endpoint_cache, mock_get_client):
        # Mock the raw LLM response (including think block)
        mock_client = MagicMock()
        mock_client.complete_code.return_value = "<think>I am thinking</think>\nimport { client } from '../client';\nimport { test, expect } from '@playwright/test';\ntest('golden test', async () => {});"
        mock_get_client.return_value = mock_client
        mock_cache_instance = MagicMock()
        mock_cache_instance.get.return_value = None
        mock_endpoint_cache.return_value = mock_cache_instance

        scenario = Scenario(
            endpoint="/test",
            method="GET",
            case_type="happy_path",
            mutation_id="golden_mut",
            expected_status=200,
            priority="high",
        )
        stage = GenerateStage("golden_run")
        # We also mock subprocess so tsc check passes
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            output = stage.run(
                scenario=scenario,
                path="/test",
                method="GET",
                operation={},
                schemas={},
                instruction="Do the golden test",
            )

        # Verify stripped think block and code matches golden snapshot
        self.assertNotIn("<think>", output.test_code)
        self.assertIn("import { client } from '../client';", output.test_code)
        self.assertEqual(output.status, "ok")
        self.assertEqual(output.scenario_id, "golden_mut")


if __name__ == "__main__":
    unittest.main()
