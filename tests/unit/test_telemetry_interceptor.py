import unittest
from unittest.mock import patch, MagicMock

from cherenkov.core.orchestrator import TestOrchestrator
from cherenkov.core.settings import get_settings
from cherenkov.core.contracts import Status


class TestTelemetryInterceptor(unittest.TestCase):
    @patch('cherenkov.core.orchestrator.DataCollector')
    @patch('cherenkov.core.orchestrator.get_settings')
    def test_telemetry_disabled_by_default(self, mock_get_settings, mock_collector):
        mock_settings = MagicMock()
        mock_settings.ENABLE_TELEMETRY = False
        mock_get_settings.return_value = mock_settings

        orchestrator = TestOrchestrator()
        
        # Mock some inputs
        mock_scenario = MagicMock()
        mock_scenario.mutation_id = "test-123"
        mock_scenario.method = "GET"
        mock_scenario.endpoint = "/users"
        from cherenkov.core.contracts import GenerateOutput, ReviewOutput, StageMeta
        
        mock_generate = GenerateOutput(
            scenario_id="test-123",
            test_code="",
            imports=[],
            status=Status.OK,
            errors=[],
            metadata=StageMeta(stage="GENERATE", duration_ms=100)
        )
        
        mock_review = ReviewOutput(
            scenario_id="test-123",
            gates=[],
            quality_score=1.0,
            status=Status.OK,
            errors=[],
            verdict="auto_approve",
            metadata=StageMeta(stage="REVIEW", duration_ms=100)
        )
        
        orchestrator.run_generate = MagicMock(return_value=mock_generate)
        orchestrator.run_review = MagicMock(return_value=mock_review)
        
        # Call the private loop runner
        ok, g_ms, r_ms = orchestrator._run_scenario(mock_scenario, "dummy.yaml", None)
        
        # Verify collector was never initialized
        mock_collector.assert_not_called()
        self.assertTrue(ok)

    @patch('cherenkov.core.orchestrator.DataCollector')
    @patch('cherenkov.core.orchestrator.get_settings')
    def test_telemetry_enabled_records_data(self, mock_get_settings, mock_collector_class):
        mock_settings = MagicMock()
        mock_settings.ENABLE_TELEMETRY = True
        mock_get_settings.return_value = mock_settings
        
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        orchestrator = TestOrchestrator()
        
        # Mock some inputs
        mock_scenario = MagicMock()
        mock_scenario.mutation_id = "test-456"
        mock_scenario.method = "GET"
        mock_scenario.endpoint = "/users"
        mock_scenario.to_dict.return_value = {"method": "GET", "endpoint": "/users"}
        
        from cherenkov.core.contracts import GenerateOutput, ReviewOutput, StageMeta, Status, Verdict
        
        mock_generate = GenerateOutput(
            scenario_id="test-456",
            test_code="test('GET /users', () => {});",
            imports=[],
            status=Status.OK,
            errors=[],
            metadata=StageMeta(stage="GENERATE", duration_ms=100)
        )
        
        mock_review = ReviewOutput(
            scenario_id="test-456",
            gates=[],
            quality_score=1.0,
            status=Status.OK,
            errors=[],
            verdict=Verdict.AUTO_APPROVE,
            metadata=StageMeta(stage="REVIEW", duration_ms=50)
        )
        
        orchestrator.run_generate = MagicMock(return_value=mock_generate)
        orchestrator.run_review = MagicMock(return_value=mock_review)
        
        # Call the private loop runner
        ok, g_ms, r_ms = orchestrator._run_scenario(mock_scenario, "dummy.yaml", None)
        
        # Verify collector was initialized and record was called
        mock_collector_class.assert_called_once()
        mock_collector.record.assert_called_once()
        
        kwargs = mock_collector.record.call_args.kwargs
        self.assertEqual(kwargs['test_code'], "test('GET /users', () => {});")
        self.assertEqual(kwargs['verdict'], "auto_approve")
        self.assertEqual(kwargs['endpoint'], "GET /users")
        self.assertEqual(kwargs['duration_ms'], 150)
