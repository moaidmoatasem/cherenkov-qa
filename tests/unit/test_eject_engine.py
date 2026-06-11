"""Unit tests for cherenkov/execution/eject.py — EjectorEngine."""
import json
import os
import tempfile
import unittest


class TestSpecFilesIn(unittest.TestCase):
    def _call(self, directory: str) -> list:
        from cherenkov.execution.eject import EjectorEngine
        return EjectorEngine._spec_files_in(directory)

    def test_nonexistent_dir_returns_empty(self):
        self.assertEqual(self._call("/no/such/path"), [])

    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self._call(d), [])

    def test_spec_ts_file_included(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "happy_path.spec.ts")
            with open(path, "w") as f:
                f.write("test content")
            result = self._call(d)
            self.assertIn("happy_path.spec.ts", result)

    def test_empty_spec_file_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.spec.ts")
            open(path, "w").close()
            self.assertEqual(self._call(d), [])

    def test_scores_json_included(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "_scores.json")
            with open(path, "w") as f:
                f.write("{}")
            self.assertIn("_scores.json", self._call(d))

    def test_non_spec_files_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("readme.md", "config.json", "test.ts"):
                with open(os.path.join(d, name), "w") as f:
                    f.write("data")
            self.assertEqual(self._call(d), [])


class TestEjectSuite(unittest.TestCase):
    def setUp(self):
        from cherenkov.execution.eject import EjectorEngine
        self.engine = EjectorEngine(run_id="test-run")

    def test_eject_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "ejected")
            result = self.engine.eject_suite(out)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(os.path.join(out, "playwright.config.ts")))
            self.assertTrue(os.path.exists(os.path.join(out, "package.json")))
            self.assertTrue(os.path.exists(os.path.join(out, "client.ts")))
            self.assertTrue(os.path.exists(os.path.join(out, "tsconfig.json")))

    def test_eject_package_json_has_playwright_dep(self):
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "ejected")
            self.engine.eject_suite(out)
            pkg = json.loads(open(os.path.join(out, "package.json")).read())
            self.assertIn("@playwright/test", pkg["devDependencies"])

    def test_eject_cleans_existing_output_dir(self):
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "ejected")
            os.makedirs(out)
            stale = os.path.join(out, "stale.txt")
            with open(stale, "w") as f:
                f.write("old")
            self.engine.eject_suite(out)
            self.assertFalse(os.path.exists(stale))

    def test_eject_client_ts_has_no_cherenkov_trace(self):
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "ejected")
            self.engine.eject_suite(out)
            content = open(os.path.join(out, "client.ts")).read()
            self.assertNotIn("cherenkov", content.lower())
