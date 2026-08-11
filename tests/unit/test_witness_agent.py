"""Unit tests for cherenkov/divergence/witness.py — WitnessAgent, _diff, _parse_repro_steps."""

import unittest
from unittest.mock import MagicMock, patch


class TestParseReproSteps(unittest.TestCase):
    """Placeholder docstring.

<description>"""
    def _call(self, steps):
        from cherenkov.divergence.witness import _parse_repro_steps

        return _parse_repro_steps(steps)

    def test_get_method_extracted(self):
        """Placeholder docstring.

:return: <description>"""
        method, path, payload, _expected = self._call(["Send GET /pets"])
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/pets")
        self.assertIsNone(payload)

    def test_post_with_body_extracted(self):
        """Placeholder docstring.

:return: <description>"""
        method, path, payload, _expected = self._call(
            ['POST /pets with body {"name": "doggie", "photoUrls": []}']
        )
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/pets")
        self.assertEqual(payload["name"], "doggie")

    def test_expected_status_extracted(self):
        """Placeholder docstring.

:return: <description>"""
        _, _, _, expected = self._call(["Send GET /pets", "Expect 404 response"])
        self.assertEqual(expected, 404)

    def test_assert_status_extracted(self):
        """Placeholder docstring.

:return: <description>"""
        _, _, _, expected = self._call(["Assert status 200"])
        self.assertEqual(expected, 200)

    def test_empty_steps_returns_defaults(self):
        """Placeholder docstring.

:return: <description>"""
        method, path, payload, expected = self._call([])
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/")
    """Placeholder docstring.

<description>"""
        self.assertIsNone(payload)
        self.assertIsNone(expected)


class TestDiff(unittest.TestCase):
    def _call(self, actual, expected, status_code=200):
        from cherenkov.divergence.witness import _diff

        return _diff(actual, expected, status_code)

    def test_status_mismatch_returns_mismatch_string(self):
        """Placeholder docstring.

:return: <description>"""
        result = self._call("body", 404, status_code=200)
        self.assertIn("mismatch", result)
        self.assertIn("404", result)

    def test_status_match_returns_no_diff(self):
        """Placeholder docstring.

:return: <description>"""
        result = self._call("body", 200, status_code=200)
        self.assertEqual(result, "no structural diff")

    def test_dict_missing_keys_reported(self):
        """Placeholder docstring.

:return: <description>"""
        actual = {"a": 1}
        expected = {"a": 1, "b": 2}
        result = self._call(actual, expected)
        self.assertIn("missing keys", result)
        self.assertIn("b", result)

    def test_dict_value_mismatch_reported(self):
        """Placeholder docstring.

:return: <description>"""
        result = self._call({"status": "fail"}, {"status": "pass"})
        self.assertIn("status", result)

    def test_identical_dicts_no_diff(self):
    """Placeholder docstring.

<description>"""
        """Placeholder docstring.

:return: <description>"""
        d = {"x": 1, "y": "hello"}
        self.assertEqual(self._call(d, d), "no structural diff")

    def test_none_expected_returns_status_and_body(self):
        """Placeholder docstring.

:return: <description>"""
        result = self._call({"key": "val"}, None, status_code=200)
        self.assertIn("status=200", result)


class TestWitnessAgentNoRepro(unittest.TestCase):
    def _make_hypothesis(self, repro_steps=None):
        from cherenkov.core.contracts import (
            DivergenceClass,
            DivergenceHypothesis,
            Severity,
        )

        return DivergenceHypothesis(
            id="h1",
            divergence_class=DivergenceClass.D1_SPEC_CODE,
            claim_a="spec says 200",
            claim_b="server returns 404",
            predicted_evidence="HTTP 404",
            severity=Severity.HIGH,
            endpoint="GET /pets",
            repro_steps=repro_steps or [],
        )

    def test_empty_repro_steps_returns_not_reproduced(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.divergence.witness import WitnessAgent

        agent = WitnessAgent("http://localhost:8000")
        result = agent.reproduce(self._make_hypothesis([]))
        self.assertFalse(result.reproduced)
        self.assertIn("No repro_steps", result.rejection_reason)

    def test_reproduce_batch_returns_one_result_per_hypothesis(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.divergence.witness import WitnessAgent

        agent = WitnessAgent("http://localhost:8000")
        hypotheses = [self._make_hypothesis([]), self._make_hypothesis([])]
        results = agent.reproduce_batch(hypotheses)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r.hypothesis_id, "h1")

    @patch("cherenkov.divergence.witness.httpx.Client")
    def test_reproduce_confirms_divergence_on_status_mismatch(self, mock_client_cls):
        """Placeholder docstring.

:param mock_client_cls: <description>
:return: <description>"""
        from cherenkov.divergence.witness import WitnessAgent

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"error": "internal"}
        mock_resp.text = '{"error": "internal"}'

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        agent = WitnessAgent("http://localhost:8000")
        hyp = self._make_hypothesis(["Send GET /pets", "Expect 200 response"])
        result = agent.reproduce(hyp)
        self.assertTrue(result.reproduced)
        self.assertIsNotNone(result.evidence)

    @patch("cherenkov.divergence.witness.httpx.Client")
    def test_reproduce_rejects_when_no_diff(self, mock_client_cls):
        """Placeholder docstring.

:param mock_client_cls: <description>
:return: <description>"""
        from cherenkov.divergence.witness import WitnessAgent

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.text = "{}"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        agent = WitnessAgent("http://localhost:8000")
        hyp = self._make_hypothesis(["Send GET /pets", "Expect 200 response"])
        result = agent.reproduce(hyp)
        self.assertFalse(result.reproduced)
        self.assertIsNone(result.evidence)

    @patch("cherenkov.divergence.witness.httpx.Client")
    def test_reproduce_handles_network_error(self, mock_client_cls):
        """Placeholder docstring.

:param mock_client_cls: <description>
:return: <description>"""
        from cherenkov.divergence.witness import WitnessAgent

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = ConnectionError("refused")
        mock_client_cls.return_value = mock_client

        agent = WitnessAgent("http://localhost:8000")
        hyp = self._make_hypothesis(["Send GET /pets"])
        result = agent.reproduce(hyp)
        self.assertFalse(result.reproduced)
        self.assertIn("Execution error", result.rejection_reason)

    @patch("cherenkov.divergence.witness.time.sleep", lambda *_: None)
    @patch("cherenkov.divergence.witness.httpx.Client")
    def test_reproduce_retries_on_429_then_detects_divergence(self, mock_client_cls):
        """Placeholder docstring.

:param mock_client_cls: <description>
:return: <description>"""
        # A rate-limited probe must not be read as conformant: back off, retry,
        # and use the real (200) response to detect the divergence.
        from cherenkov.divergence.witness import WitnessAgent

        r429 = MagicMock(status_code=429, headers={})
        r429.json.return_value = {}
        r429.text = ""
        r200 = MagicMock(status_code=500)  # 500 vs expected 200 -> divergence
        r200.json.return_value = {"error": "boom"}
        r200.text = '{"error": "boom"}'

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [r429, r429, r200]
        mock_client_cls.return_value = mock_client

        agent = WitnessAgent("http://localhost:8000")
        result = agent.reproduce(
            self._make_hypothesis(["Send GET /pets", "Expect 200 response"])
        )
        self.assertEqual(mock_client.get.call_count, 3)  # retried past both 429s
        self.assertTrue(result.reproduced)

    @patch("cherenkov.divergence.witness.time.sleep", lambda *_: None)
    @patch("cherenkov.divergence.witness.httpx.Client")
    def test_reproduce_429_retries_are_bounded(self, mock_client_cls):
        """Placeholder docstring.

:param mock_client_cls: <description>
:return: <description>"""
        # Persistent throttling must not hang the run: retries are capped.
        from cherenkov.divergence.witness import WitnessAgent

        r429 = MagicMock(status_code=429, headers={})
        r429.json.return_value = {}
        r429.text = ""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = r429
        mock_client_cls.return_value = mock_client

        agent = WitnessAgent("http://localhost:8000")
        agent.reproduce(self._make_hypothesis(["Send GET /pets", "Expect 200 response"]))
        # 1 initial + _MAX_RETRIES_429 retries
        self.assertEqual(
            mock_client.get.call_count, 1 + WitnessAgent._MAX_RETRIES_429
        )

    def test_retry_after_header_parsed_and_bounded(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.divergence.witness import _retry_after_seconds

        self.assertEqual(_retry_after_seconds(MagicMock(headers={"Retry-After": "2"})), 2.0)
        self.assertEqual(_retry_after_seconds(MagicMock(headers={"Retry-After": "999"})), 5.0)
        self.assertIsNone(_retry_after_seconds(MagicMock(headers={})))
        self.assertIsNone(_retry_after_seconds(MagicMock(headers={"Retry-After": "soon"})))
