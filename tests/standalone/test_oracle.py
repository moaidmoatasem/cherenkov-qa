"""Tests for E4-3: Oracle SPI."""

import unittest
from unittest.mock import patch, MagicMock

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType
from cherenkov.oracle.interface import Oracle, OracleResult
from cherenkov.oracle.spec_prism import SpecPrismOracle
from cherenkov.oracle.prod_snapshot import ProdSnapshotOracle


class TestOracleInterface(unittest.TestCase):
    def test_interface_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Oracle()

    def test_oracle_result_defaults(self):
        r = OracleResult(is_correct=True)
        self.assertTrue(r.is_correct)
        self.assertEqual(r.confidence, 1.0)
        self.assertEqual(r.detail, "")
        self.assertIsNone(r.expected)
        self.assertIsNone(r.actual)

    def test_oracle_result_custom(self):
        r = OracleResult(
            is_correct=False,
            confidence=0.5,
            detail="mismatch",
            expected=200,
            actual=404,
        )
        self.assertFalse(r.is_correct)
        self.assertEqual(r.confidence, 0.5)
        self.assertEqual(r.detail, "mismatch")
        self.assertEqual(r.expected, 200)
        self.assertEqual(r.actual, 404)


class TestSpecPrismOracle(unittest.TestCase):
    def setUp(self):
        self.oracle = SpecPrismOracle(prism_url="http://localhost:4010")
        self.claim = Claim(
            id="test-1",
            category="endpoint",
            subject="GET /api/health",
            value={"status": 200},
            provenance=Provenance(
                source_type=ProvenanceType.SPEC, source_uri="spec.yaml"
            ),
        )

    @patch("cherenkov.oracle.spec_prism.requests.request")
    def test_evaluate_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_request.return_value = mock_resp

        result = self.oracle.evaluate(self.claim)
        self.assertTrue(result.is_correct)
        self.assertGreaterEqual(result.confidence, 0.5)

    def test_non_evaluable_category(self):
        non_eval_claim = Claim(
            id="test-2",
            category="mutation",
            subject="POST /api/users",
            value={},
            provenance=Provenance(
                source_type=ProvenanceType.SPEC, source_uri="spec.yaml"
            ),
        )
        result = self.oracle.evaluate(non_eval_claim)
        self.assertFalse(result.is_correct)
        self.assertEqual(result.confidence, 0.5)

    @patch("cherenkov.oracle.spec_prism.requests.request")
    def test_prism_unreachable(self, mock_request):
        import requests as req_lib

        mock_request.side_effect = req_lib.exceptions.ConnectionError(
            "Connection refused"
        )

        result = self.oracle.evaluate(self.claim)
        self.assertFalse(result.is_correct)
        self.assertEqual(result.confidence, 0.3)


class TestProdSnapshotOracle(unittest.TestCase):
    def setUp(self):
        self.oracle = ProdSnapshotOracle(prod_base_url="https://api.example.com")
        self.claim = Claim(
            id="test-1",
            category="endpoint",
            subject="GET /health",
            value={"status": 200},
            provenance=Provenance(
                source_type=ProvenanceType.TRAFFIC, source_uri="capture.har"
            ),
        )

    @patch("cherenkov.oracle.prod_snapshot.requests.request")
    def test_evaluate_match(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_request.return_value = mock_resp

        result = self.oracle.evaluate(self.claim)
        self.assertTrue(result.is_correct)

    @patch("cherenkov.oracle.prod_snapshot.requests.request")
    def test_evaluate_mismatch(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_request.return_value = mock_resp

        result = self.oracle.evaluate(self.claim)
        self.assertFalse(result.is_correct)
        self.assertEqual(result.expected, 500)
        self.assertEqual(result.actual, 200)

    def test_non_evaluable_category(self):
        non_eval_claim = Claim(
            id="test-2",
            category="shape",
            subject="UserSchema",
            value={},
            provenance=Provenance(
                source_type=ProvenanceType.CODE, source_uri="code.py"
            ),
        )
        result = self.oracle.evaluate(non_eval_claim)
        self.assertTrue(result.is_correct)


if __name__ == "__main__":
    unittest.main()
