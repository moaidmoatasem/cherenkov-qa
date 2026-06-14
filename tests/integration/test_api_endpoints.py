from cherenkov.core.settings import get_settings
"""
Integration tests for cherenkov/web/api.py — covers all core REST endpoints.

Uses FastAPI's TestClient (synchronous ASGI wrapper) with minimal mocking of
external services (Ollama, OrchestrationEngine, ValidationEngine, EjectorEngine)
so tests run offline and fast.  No CHERENKOV_HITL_API_KEY → auth disabled.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("CHERENKOV_ENV", "development")

from fastapi.testclient import TestClient
from cherenkov.web.api import app


def _make_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── Health ────────────────────────────────────────────────────────────────────


class TestHealth(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    @patch.object(get_settings(), "detect_ollama_device", return_value="cpu")
    def test_health_200(self, _):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "online")
        self.assertIn("device", body)
        self.assertIn("gen_model", body)

    @patch(
        "cherenkov.core.config.get_settings().detect_ollama_device",
        side_effect=RuntimeError("no ollama"),
    )
    def test_health_degrades_gracefully_on_ollama_error(self, _):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "online")


# ── Tests list ────────────────────────────────────────────────────────────────


class TestListTests(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_empty_when_no_generated_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                r = self.client.get("/api/v1/tests")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_returns_spec_files_in_generated_tests_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_dir = os.path.join(tmpdir, "stub", "generated_tests")
            os.makedirs(tests_dir)
            spec = os.path.join(tests_dir, "POST_users.spec.ts")
            with open(spec, "w") as f:
                f.write("test('ok', () => {})")
            with patch("os.getcwd", return_value=tmpdir):
                r = self.client.get("/api/v1/tests")
        self.assertEqual(r.status_code, 200)
        items = r.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "POST_users.spec.ts")


# ── Review queue ──────────────────────────────────────────────────────────────


class TestReviewQueue(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_queue_returns_list(self):
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.list.return_value = []
            r = self.client.get("/api/v1/review/queue")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_queue_serialises_items(self):
        item = MagicMock()
        item.id = "s1"
        item.endpoint = "/users"
        item.method = "POST"
        item.confidence = 0.85
        item.confidence_reason = "high"
        item.review_gate_failed = False
        item.status.value = "pending"
        item.created_at = "2026-01-01T00:00:00Z"
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.list.return_value = [item]
            r = self.client.get("/api/v1/review/queue")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], "s1")
        self.assertEqual(body[0]["endpoint"], "/users")


# ── Review approve / reject ───────────────────────────────────────────────────


class TestReviewApprove(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_approve_404_for_unknown_item(self):
        err = MagicMock()
        err.ok = False
        err.error = MagicMock(code="not_found", message="not found")
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.approve.return_value = err
            r = self.client.post(
                "/api/v1/review/approve",
                json={"scenario_id": "nonexistent"},
            )
        self.assertEqual(r.status_code, 404)

    def test_approve_success(self):
        env = MagicMock(ok=True)
        with patch("cherenkov.web.api.get_queue") as mock_q, patch(
            "cherenkov.web.api.FeedbackStore"
        ), patch("cherenkov.reflector.reflector.Reflector"):
            mock_q.return_value.approve.return_value = env
            r = self.client.post(
                "/api/v1/review/approve",
                json={"scenario_id": "scenario-1", "reason": "looks good"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "approved")

    def test_approve_409_on_conflict(self):
        err = MagicMock()
        err.ok = False
        err.error = MagicMock(code="conflict", message="already approved")
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.approve.return_value = err
            r = self.client.post(
                "/api/v1/review/approve",
                json={"scenario_id": "s1"},
            )
        self.assertEqual(r.status_code, 409)


class TestReviewReject(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_reject_404_for_unknown_item(self):
        err = MagicMock()
        err.ok = False
        err.error = MagicMock(code="not_found", message="not found")
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.reject.return_value = err
            r = self.client.post(
                "/api/v1/review/reject",
                json={"scenario_id": "nonexistent", "reason": "flaky"},
            )
        self.assertEqual(r.status_code, 404)

    def test_reject_success(self):
        env = MagicMock(ok=True)
        with patch("cherenkov.web.api.get_queue") as mock_q, patch(
            "cherenkov.web.api.FeedbackStore"
        ), patch("cherenkov.reflector.reflector.Reflector"):
            mock_q.return_value.reject.return_value = env
            r = self.client.post(
                "/api/v1/review/reject",
                json={"scenario_id": "scenario-1", "reason": "wrong assertion"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "rejected")


# ── Review edit ───────────────────────────────────────────────────────────────


class TestReviewEdit(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_edit_saves_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                r = self.client.post(
                    "/api/v1/review/edit",
                    json={
                        "scenario_id": "post_users",
                        "test_code": "test('ok', () => {})",
                    },
                )
            self.assertEqual(r.status_code, 200)
            saved = os.path.join(
                tmpdir, "stub", "generated_tests", "post_users.spec.ts"
            )
            self.assertTrue(os.path.exists(saved))

    def test_edit_400_missing_test_code(self):
        r = self.client.post(
            "/api/v1/review/edit",
            json={"scenario_id": "post_users"},
        )
        self.assertEqual(r.status_code, 400)

    def test_edit_400_invalid_scenario_id(self):
        r = self.client.post(
            "/api/v1/review/edit",
            json={"scenario_id": "../../../etc/passwd", "test_code": "evil"},
        )
        self.assertEqual(r.status_code, 400)


# ── Review classify ───────────────────────────────────────────────────────────


class TestReviewClassify(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_classify_400_for_unknown_value(self):
        with patch("cherenkov.web.api.get_queue"):
            r = self.client.post(
                "/api/v1/review/classify",
                json={"item_id": "s1", "classification": "not-a-real-class"},
            )
        self.assertEqual(r.status_code, 400)

    def test_classify_regression_routes_to_approve(self):
        env = MagicMock(ok=True)
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.approve.return_value = env
            r = self.client.post(
                "/api/v1/review/classify",
                json={"item_id": "s1", "classification": "regression"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["classification"], "regression")

    def test_classify_intended_routes_to_reject(self):
        env = MagicMock(ok=True)
        with patch("cherenkov.web.api.get_queue") as mock_q:
            mock_q.return_value.reject.return_value = env
            r = self.client.post(
                "/api/v1/review/classify",
                json={"item_id": "s1", "classification": "intended"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["classification"], "intended")


# ── Eject ─────────────────────────────────────────────────────────────────────


class TestEject(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_eject_400_for_path_traversal(self):
        r = self.client.post(
            "/api/v1/eject",
            json={"output_path": "/etc/passwd"},
        )
        self.assertEqual(r.status_code, 400)

    def test_eject_success(self):
        mock_engine = MagicMock()
        mock_engine.eject_suite.return_value = True
        out = os.path.abspath(os.path.join(os.getcwd(), "test_eject_output"))
        with patch("cherenkov.execution.eject.EjectorEngine", return_value=mock_engine):
            r = self.client.post("/api/v1/eject", json={"output_path": out})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ejected")

    def test_eject_500_when_engine_raises(self):
        mock_engine = MagicMock()
        mock_engine.eject_suite.side_effect = RuntimeError("disk full")
        out = os.path.abspath(os.path.join(os.getcwd(), "test_eject_output"))
        with patch("cherenkov.execution.eject.EjectorEngine", return_value=mock_engine):
            r = self.client.post("/api/v1/eject", json={"output_path": out})
        self.assertEqual(r.status_code, 500)

    def test_eject_500_when_engine_returns_false(self):
        mock_engine = MagicMock()
        mock_engine.eject_suite.return_value = False
        out = os.path.abspath(os.path.join(os.getcwd(), "test_eject_output"))
        with patch("cherenkov.execution.eject.EjectorEngine", return_value=mock_engine):
            r = self.client.post("/api/v1/eject", json={"output_path": out})
        self.assertEqual(r.status_code, 500)


# ── Divergences ───────────────────────────────────────────────────────────────


class TestDivergences(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_list_returns_list(self):
        with patch("cherenkov.web.divergences.list_divergences", return_value=[]):
            r = self.client.get("/api/v1/divergences")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_act_404_for_unknown_divergence(self):
        with patch(
            "cherenkov.web.divergences.apply_action", side_effect=KeyError("unknown")
        ):
            r = self.client.post(
                "/api/v1/divergences/act",
                json={"divergence_id": "x", "action": "accept"},
            )
        self.assertEqual(r.status_code, 404)

    def test_act_400_for_invalid_action(self):
        with patch(
            "cherenkov.web.divergences.apply_action",
            side_effect=ValueError("bad action"),
        ):
            r = self.client.post(
                "/api/v1/divergences/act",
                json={"divergence_id": "d1", "action": "not_a_real_action"},
            )
        self.assertEqual(r.status_code, 400)


# ── Overview / Truth-map / Failures / Metrics ─────────────────────────────────


class TestDashboardEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def _mock_kpi(self):
        return {
            "false_positive_rate": 0.05,
            "maintenance_efficiency": 0.90,
            "defect_escape_count": 2,
            "total_verdicts": 40,
        }

    def test_overview_200(self):
        with patch("cherenkov.ai.accounting.CostAccountant") as MockCA, patch(
            "cherenkov.web.api.FeedbackStore"
        ) as MockFS:
            MockCA.return_value.get_governance_kpis.return_value = self._mock_kpi()
            MockFS.return_value.get_all.return_value = []
            r = self.client.get("/api/v1/overview")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("falsePositiveRate", body)
        self.assertIn("totalVerdicts", body)

    def test_truth_map_200(self):
        with patch("cherenkov.reflector.store.VerdictStore") as MockVS:
            MockVS.return_value.list_idioms.return_value = []
            r = self.client.get("/api/v1/truth-map")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_failures_200(self):
        with patch("cherenkov.reflector.store.VerdictStore") as MockVS:
            mock_store = MockVS.return_value
            mock_store.db_path = ":memory:"
            r = self.client.get("/api/v1/failures")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_metrics_200(self):
        report = MagicMock(
            request_count=10,
            total_tokens=5000,
            total_cost=0.02,
            total_duration_ms=12000,
        )
        with patch("cherenkov.ai.accounting.CostAccountant") as MockCA:
            MockCA.return_value.report = report
            MockCA.return_value.get_governance_kpis.return_value = self._mock_kpi()
            r = self.client.get("/api/v1/metrics")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("requestCount", r.json()["metrics"])


# ── Mobile pilot ──────────────────────────────────────────────────────────────


class TestMobilePilot(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_status_returns_idle_by_default(self):
        r = self.client.get("/api/v1/mobile/pilot/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("status", body)
        self.assertIn("steps", body)

    def test_start_sets_running(self):
        r = self.client.post("/api/v1/mobile/pilot/start")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "started")


# ── Ingest edge cases ─────────────────────────────────────────────────────────


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_ingest_400_when_no_file_and_no_url(self):
        r = self.client.post("/api/v1/ingest")
        self.assertEqual(r.status_code, 400)

    def test_ingest_400_on_blocked_internal_url(self):
        r = self.client.post(
            "/api/v1/ingest",
            data={"url": "http://localhost/spec.yaml"},
        )
        self.assertEqual(r.status_code, 400)

    def test_ingest_400_on_private_ip_url(self):
        r = self.client.post(
            "/api/v1/ingest",
            data={"url": "http://192.168.1.1/spec.yaml"},
        )
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
