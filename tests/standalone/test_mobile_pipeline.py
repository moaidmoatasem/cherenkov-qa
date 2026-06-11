"""
Unit tests for the mobile testing pipeline.

Covers: parsers, adapter, plan/generate/review stages,
        runners (mocked), ejectors, and the MobileRAGIndex.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow, MobileScreen
from cherenkov.sources.mobile.parsers import APKParser, HARParser, HILParser
from cherenkov.sources.mobile.adapter import MobileSourceAdapter
from cherenkov.stages.mobile_plan import MobilePlanStage, MobileScenario
from cherenkov.stages.mobile_generate import MobileGenerateStage, MobileGenerateOutput
from cherenkov.stages.mobile_review import MobileReviewStage
from cherenkov.execution.maestro_runner import MaestroRunner
from cherenkov.execution.appium_runner import AppiumRunner
from cherenkov.execution.mobile_eject_maestro import MaestroEjector
from cherenkov.execution.mobile_eject_appium import AppiumEjector
from cherenkov.rag.mobile_index import MobileRAGIndex


# ── Contracts ────────────────────────────────────────────────────────────────

class TestContracts(unittest.TestCase):
    def test_mobile_app_fields(self):
        app = MobileApp(app_id="com.foo", name="Foo", platform="android", version="1.0", package_path="/tmp/foo.apk")
        self.assertEqual(app.app_id, "com.foo")
        self.assertEqual(app.platform, "android")

    def test_mobile_screen_fields(self):
        screen = MobileScreen(screen_id="s1", name="Home", elements=[{"id": "btn"}], navigation=["login"])
        self.assertEqual(screen.screen_id, "s1")
        self.assertEqual(len(screen.elements), 1)

    def test_mobile_flow_fields(self):
        flow = MobileFlow(flow_id="f1", name="Login", screens=["home", "auth"], actions=[{"tap": "submit"}])
        self.assertEqual(flow.flow_id, "f1")
        self.assertEqual(flow.screens, ["home", "auth"])


# ── HARParser ────────────────────────────────────────────────────────────────

class TestHARParser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, data: dict, name: str = "test.har") -> str:
        path = os.path.join(self.tmp, name)
        Path(path).write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_parse_standard_log_format(self):
        path = self._write({
            "log": {
                "entries": [
                    {"request": {"url": "https://api.example.com/login", "method": "POST"},
                     "response": {"status": 200}},
                ]
            }
        })
        entries = HARParser().parse(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["url"], "https://api.example.com/login")
        self.assertEqual(entries[0]["method"], "POST")
        self.assertEqual(entries[0]["status"], 200)

    def test_parse_flat_entries_format(self):
        path = self._write({
            "entries": [
                {"request": {"url": "https://api.example.com/data", "method": "GET"},
                 "response": {"status": 404}},
            ]
        })
        entries = HARParser().parse(path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], 404)

    def test_parse_empty_har(self):
        path = self._write({"log": {"entries": []}})
        entries = HARParser().parse(path)
        self.assertEqual(entries, [])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            HARParser().parse("/nonexistent/path.har")

    def test_multiple_entries(self):
        path = self._write({
            "log": {
                "entries": [
                    {"request": {"url": "/a", "method": "GET"}, "response": {"status": 200}},
                    {"request": {"url": "/b", "method": "POST"}, "response": {"status": 201}},
                    {"request": {"url": "/c", "method": "DELETE"}, "response": {"status": 204}},
                ]
            }
        })
        entries = HARParser().parse(path)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[2]["method"], "DELETE")


# ── HILParser ────────────────────────────────────────────────────────────────

class TestHILParser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, data, name: str = "test.hil") -> str:
        path = os.path.join(self.tmp, name)
        Path(path).write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_parse_list_format(self):
        path = self._write([
            {"flow_id": "f1", "name": "Login", "screens": ["home"], "actions": []},
        ])
        flows = HILParser().parse(path)
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0].flow_id, "f1")
        self.assertEqual(flows[0].name, "Login")

    def test_parse_dict_flows_format(self):
        path = self._write({
            "flows": [
                {"flow_id": "f2", "name": "Checkout", "screens": ["cart", "pay"], "actions": [{"tap": "pay"}]},
            ]
        })
        flows = HILParser().parse(path)
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0].flow_id, "f2")

    def test_parse_auto_generates_flow_id(self):
        path = self._write([{"name": "No ID Flow"}])
        flows = HILParser().parse(path)
        self.assertEqual(flows[0].flow_id, "flow_0")

    def test_parse_empty_list(self):
        path = self._write([])
        flows = HILParser().parse(path)
        self.assertEqual(flows, [])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            HILParser().parse("/nonexistent/path.hil")

    def test_actions_preserved(self):
        path = self._write([{"flow_id": "f3", "name": "Search", "screens": [], "actions": [{"tap": "search"}, {"type": "query"}]}])
        flows = HILParser().parse(path)
        self.assertEqual(len(flows[0].actions), 2)


# ── MobileSourceAdapter ──────────────────────────────────────────────────────

class TestMobileSourceAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_dispatch_har(self):
        path = os.path.join(self.tmp, "traffic.har")
        Path(path).write_text(json.dumps({"log": {"entries": []}}))
        result = MobileSourceAdapter().ingest(path)
        self.assertIsInstance(result, list)

    def test_dispatch_hil(self):
        path = os.path.join(self.tmp, "trace.hil")
        Path(path).write_text(json.dumps([]))
        result = MobileSourceAdapter().ingest(path)
        self.assertIsInstance(result, list)

    def test_unsupported_extension_raises(self):
        path = os.path.join(self.tmp, "file.xyz")
        Path(path).write_text("{}")
        with self.assertRaises(ValueError) as ctx:
            MobileSourceAdapter().ingest(path)
        self.assertIn(".xyz", str(ctx.exception))

    def test_custom_parsers_are_used(self):
        mock_har = MagicMock()
        mock_har.parse.return_value = [{"url": "/stub", "method": "GET", "status": 200}]
        adapter = MobileSourceAdapter(har_parser=mock_har)

        path = os.path.join(self.tmp, "stub.har")
        Path(path).write_text(json.dumps({"log": {"entries": []}}))
        result = adapter.ingest(path)
        mock_har.parse.assert_called_once_with(path)
        self.assertEqual(result[0]["url"], "/stub")

    def test_apk_dispatches_to_apk_parser(self):
        mock_apk = MagicMock()
        mock_apk.parse.return_value = MobileApp("com.test", "Test", "android", "1.0", "/tmp/test.apk")
        adapter = MobileSourceAdapter(apk_parser=mock_apk)

        path = os.path.join(self.tmp, "app.apk")
        Path(path).write_text("fake apk")
        result = adapter.ingest(path)
        mock_apk.parse.assert_called_once_with(path)
        self.assertEqual(result.app_id, "com.test")


# ── MobilePlanStage ──────────────────────────────────────────────────────────

class TestMobilePlanStage(unittest.TestCase):
    def test_run_returns_ok(self):
        out = MobilePlanStage().run()
        self.assertEqual(out.status, "ok")

    def test_run_returns_scenarios(self):
        out = MobilePlanStage().run()
        self.assertGreaterEqual(len(out.scenarios), 1)

    def test_scenarios_have_required_fields(self):
        out = MobilePlanStage().run()
        for s in out.scenarios:
            self.assertTrue(s.id, "scenario id should be non-empty")
            self.assertTrue(s.name, "scenario name should be non-empty")
            self.assertIsInstance(s.steps, list)
            self.assertGreater(len(s.steps), 0)

    def test_run_id_logged(self):
        stage = MobilePlanStage(run_id="test-run")
        out = stage.run()
        self.assertEqual(out.status, "ok")

    def test_ingest_output_accepted(self):
        out = MobilePlanStage().run(ingest_output={"app_id": "com.test"})
        self.assertEqual(out.status, "ok")


# ── MobileGenerateStage ───────────────────────────────────────────────────────

class TestMobileGenerateStage(unittest.TestCase):
    def _scenario(self, sid="s001", name="test", steps=None):
        return MobileScenario(id=sid, name=name, description="desc", steps=steps or ["launch app", "tap button"])

    def test_run_returns_generate_output(self):
        out = MobileGenerateStage().run(self._scenario())
        self.assertEqual(out.scenario_id, "s001")
        self.assertEqual(out.status, "ok")

    def test_yaml_contains_app_id(self):
        out = MobileGenerateStage().run(self._scenario())
        self.assertIn("appId:", out.yaml_content)

    def test_yaml_non_empty(self):
        out = MobileGenerateStage().run(self._scenario())
        self.assertTrue(out.yaml_content.strip())

    def test_tap_step_generates_tapOn(self):
        s = self._scenario(steps=["tap login button"])
        out = MobileGenerateStage().run(s)
        self.assertIn("tapOn:", out.yaml_content)

    def test_enter_step_generates_inputText(self):
        s = self._scenario(steps=["enter username"])
        out = MobileGenerateStage().run(s)
        self.assertIn("inputText:", out.yaml_content)

    def test_launch_step_generates_waitFor(self):
        s = self._scenario(steps=["launch app"])
        out = MobileGenerateStage().run(s)
        self.assertIn("waitFor:", out.yaml_content)

    def test_capture_step_generates_takeScreenshot(self):
        s = self._scenario(steps=["capture screenshot"])
        out = MobileGenerateStage().run(s)
        self.assertIn("takeScreenshot:", out.yaml_content)

    def test_verify_step_generates_assertVisible(self):
        s = self._scenario(steps=["verify dashboard visible"])
        out = MobileGenerateStage().run(s)
        self.assertIn("assertVisible:", out.yaml_content)


# ── MobileReviewStage ─────────────────────────────────────────────────────────

class TestMobileReviewStage(unittest.TestCase):
    def _make_output(self, yaml_content: str, sid: str = "s001") -> MobileGenerateOutput:
        return MobileGenerateOutput(scenario_id=sid, yaml_content=yaml_content)

    def test_valid_yaml_passes(self):
        yaml_content = "appId: com.example.app\n---\nname: test\n\n- tapOn:\n    text: \"Login\"\n"
        out = MobileReviewStage().run(self._make_output(yaml_content))
        self.assertTrue(out.passed)
        self.assertEqual(out.errors, [])

    def test_empty_yaml_fails(self):
        out = MobileReviewStage().run(self._make_output(""))
        self.assertFalse(out.passed)
        self.assertTrue(any("empty" in e.lower() for e in out.errors))

    def test_missing_app_id_fails(self):
        yaml_content = "---\nname: test\n- tapOn:\n    text: \"Login\"\n"
        out = MobileReviewStage().run(self._make_output(yaml_content))
        self.assertFalse(out.passed)
        self.assertTrue(any("appId" in e for e in out.errors))

    def test_no_commands_fails(self):
        yaml_content = "appId: com.example.app\n---\nname: test\n"
        out = MobileReviewStage().run(self._make_output(yaml_content))
        self.assertFalse(out.passed)

    def test_scenario_id_preserved(self):
        yaml_content = "appId: com.example.app\n---\n- tapOn:\n    text: \"X\"\n"
        out = MobileReviewStage().run(self._make_output(yaml_content, "m999"))
        self.assertEqual(out.scenario_id, "m999")

    def test_status_ok(self):
        yaml_content = "appId: com.example.app\n---\n- assertVisible:\n    text: \"Y\"\n"
        out = MobileReviewStage().run(self._make_output(yaml_content))
        self.assertEqual(out.status, "ok")


# ── MaestroRunner ─────────────────────────────────────────────────────────────

class TestMaestroRunner(unittest.TestCase):
    def test_health_check_returns_false_when_binary_missing(self):
        runner = MaestroRunner(maestro_binary="maestro-not-installed-xyzzy")
        self.assertFalse(runner.health_check())

    @patch("cherenkov.execution.maestro_runner.subprocess.run")
    def test_health_check_true_when_version_succeeds(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        runner = MaestroRunner()
        self.assertTrue(runner.health_check())

    @patch("cherenkov.execution.maestro_runner.subprocess.run")
    def test_run_test_passed_on_returncode_0(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="passed", stderr="")
        result = MaestroRunner().run_test("flow.yaml")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["stdout"], "passed")

    @patch("cherenkov.execution.maestro_runner.subprocess.run")
    def test_run_test_failed_on_nonzero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = MaestroRunner().run_test("flow.yaml")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stderr"], "error")

    @patch("cherenkov.execution.maestro_runner.subprocess.run")
    def test_run_directory_passes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="all good", stderr="")
        result = MaestroRunner().run_directory("/some/dir")
        self.assertEqual(result["status"], "passed")


# ── AppiumRunner ──────────────────────────────────────────────────────────────

class TestAppiumRunner(unittest.TestCase):
    def test_health_check_returns_false_when_server_unreachable(self):
        runner = AppiumRunner(appium_server="http://127.0.0.1:19998")
        self.assertFalse(runner.health_check())

    @patch("cherenkov.execution.appium_runner.requests.get")
    def test_health_check_true_when_server_ok(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        runner = AppiumRunner()
        self.assertTrue(runner.health_check())

    @patch("cherenkov.execution.appium_runner.requests.get")
    def test_health_check_false_on_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        self.assertFalse(AppiumRunner().health_check())

    def test_run_test_missing_file(self):
        result = AppiumRunner().run_test("/nonexistent/test_file.py")
        self.assertEqual(result["status"], "failed")
        self.assertIn("not found", result["error"])

    @patch("cherenkov.execution.appium_runner.subprocess.run")
    def test_run_test_passed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="1 passed", stderr="")
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"def test_dummy(): pass")
            path = f.name
        try:
            result = AppiumRunner().run_test(path)
            self.assertEqual(result["status"], "passed")
        finally:
            os.unlink(path)


# ── MaestroEjector ────────────────────────────────────────────────────────────

class TestMaestroEjector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_eject_single_test(self):
        yaml_content = "name: login_flow\nappId: com.example.app\nsteps:\n  - tapOn: Login\n"
        ejector = MaestroEjector()
        path = ejector.eject(yaml_content, self.tmp)
        files = list(path.iterdir())
        yaml_files = [f for f in files if f.suffix == ".yaml"]
        self.assertGreater(len(yaml_files), 0)

    def test_eject_writes_readme(self):
        yaml_content = "name: test\nappId: com.example.app\n"
        ejector = MaestroEjector()
        path = ejector.eject(yaml_content, self.tmp)
        readme = path / "README.md"
        self.assertTrue(readme.exists())
        content = readme.read_text()
        self.assertIn("maestro test", content)

    def test_eject_creates_output_dir(self):
        out_dir = os.path.join(self.tmp, "nested", "output")
        yaml_content = "name: t\nappId: com.example.app\n"
        MaestroEjector().eject(yaml_content, out_dir)
        self.assertTrue(Path(out_dir).exists())

    def test_eject_sanitizes_filenames(self):
        yaml_content = "name: \"My Test: With Spaces!\"\nappId: com.example.app\n"
        path = MaestroEjector().eject(yaml_content, self.tmp)
        yaml_files = [f.name for f in path.iterdir() if f.suffix == ".yaml"]
        for name in yaml_files:
            self.assertFalse(any(c in name for c in "!: "), f"unsafe chars in filename: {name}")


# ── AppiumEjector ─────────────────────────────────────────────────────────────

class TestAppiumEjector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _eject(self, yaml_content: str) -> Path:
        return AppiumEjector().eject(yaml_content, self.tmp)

    def test_eject_creates_test_file(self):
        path = self._eject("name: login_test\nsteps:\n  - tapOn: Login\n")
        py_files = [f for f in path.iterdir() if f.name.startswith("test_") and f.suffix == ".py"]
        self.assertGreater(len(py_files), 0)

    def test_eject_writes_conftest(self):
        path = self._eject("name: test\nsteps: []\n")
        conftest = path / "conftest.py"
        self.assertTrue(conftest.exists())
        content = conftest.read_text()
        self.assertIn("@pytest.fixture", content)
        self.assertIn("webdriver.Remote", content)

    def test_eject_writes_requirements(self):
        path = self._eject("name: test\nsteps: []\n")
        req = path / "requirements.txt"
        self.assertTrue(req.exists())
        content = req.read_text()
        self.assertIn("Appium-Python-Client", content)
        self.assertIn("pytest", content)

    def test_eject_writes_readme(self):
        path = self._eject("name: test\nsteps: []\n")
        readme = path / "README.md"
        self.assertTrue(readme.exists())
        self.assertIn("appium", readme.read_text().lower())

    def test_eject_tapOn_generates_click(self):
        path = self._eject("name: tap_test\nsteps:\n  - tapOn: Login Button\n")
        py_files = [f for f in path.iterdir() if f.name.startswith("test_") and f.suffix == ".py"]
        content = py_files[0].read_text()
        self.assertIn("click()", content)

    def test_eject_assertVisible_generates_assert(self):
        path = self._eject("name: assert_test\nsteps:\n  - assertVisible: Welcome\n")
        py_files = [f for f in path.iterdir() if f.name.startswith("test_") and f.suffix == ".py"]
        content = py_files[0].read_text()
        self.assertIn("assert", content)


# ── MobileRAGIndex ────────────────────────────────────────────────────────────

class TestMobileRAGIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "test_mobile.db")
        self.idx = MobileRAGIndex(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_creates_database(self):
        self.assertTrue(Path(self.db_path).exists())

    def test_index_and_query_app(self):
        self.idx.index_app("com.myapp", "My App", "android", "e-commerce shopping login")
        results = self.idx.query("login")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["app_id"], "com.myapp")

    def test_query_returns_empty_for_no_match(self):
        self.idx.index_app("com.other", "Other", "ios", "music streaming")
        results = self.idx.query("zzzz_nonexistent_xyz")
        self.assertEqual(results, [])

    def test_screens_and_flows_deserialized(self):
        screens = [{"id": "home"}, {"id": "login"}]
        flows = [{"flow_id": "f1", "name": "Login"}]
        self.idx.index_app("com.app", "App", "android", "login", screens=screens, flows=flows)
        results = self.idx.query("login")
        self.assertIsInstance(results[0]["screens"], list)
        self.assertIsInstance(results[0]["flows"], list)
        self.assertEqual(len(results[0]["screens"]), 2)

    def test_reindex_replaces_existing(self):
        self.idx.index_app("com.app", "App v1", "android", "old description")
        self.idx.index_app("com.app", "App v2", "android", "updated new description")
        results = self.idx.query("updated")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "App v2")

    def test_limit_respected(self):
        for i in range(5):
            self.idx.index_app(f"com.app{i}", f"App {i}", "android", "common keyword shared")
        results = self.idx.query("common", limit=3)
        self.assertLessEqual(len(results), 3)

    def test_multiple_platforms(self):
        self.idx.index_app("com.android_app", "Android App", "android", "payment checkout")
        self.idx.index_app("com.ios_app", "iOS App", "ios", "payment invoice checkout")
        results = self.idx.query("payment")
        app_ids = {r["app_id"] for r in results}
        self.assertIn("com.android_app", app_ids)
        self.assertIn("com.ios_app", app_ids)


if __name__ == "__main__":
    unittest.main()
