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


class TestZeroLockIn(unittest.TestCase):
    """E1.4 — prove zero lock-in: ejected suite has no cherenkov dependency anywhere."""

    def setUp(self):
        from cherenkov.execution.eject import EjectorEngine
        self.engine = EjectorEngine(run_id="test-e1.4")

    def _eject(self, base: str) -> str:
        out = os.path.join(base, "ejected")
        self.assertTrue(self.engine.eject_suite(out), "eject_suite must succeed")
        return out

    def test_lock_in_audit_passes_on_ejected_suite(self):
        """Full lock-in audit must find zero violations after eject."""
        with tempfile.TemporaryDirectory() as base:
            out = self._eject(base)
            audit = self.engine.audit_lock_in(out)
            self.assertTrue(
                audit.clean,
                f"Lock-in violations found: {audit.violations}",
            )

    def test_package_json_has_no_cherenkov_dependency(self):
        """package.json must not list cherenkov as a dependency."""
        with tempfile.TemporaryDirectory() as base:
            out = self._eject(base)
            pkg = json.loads(open(os.path.join(out, "package.json")).read())
            all_deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
                **pkg.get("peerDependencies", {}),
            }
            cherenkov_deps = [k for k in all_deps if "cherenkov" in k.lower()]
            self.assertEqual(
                cherenkov_deps, [],
                f"package.json still references cherenkov: {cherenkov_deps}",
            )

    def test_spec_files_have_no_cherenkov_import(self):
        """Every .spec.ts in the ejected suite must import only from standard packages."""
        with tempfile.TemporaryDirectory() as base:
            out = self._eject(base)
            tests_dir = os.path.join(out, "tests")
            spec_files = [f for f in os.listdir(tests_dir) if f.endswith(".spec.ts")]
            self.assertTrue(spec_files, "At least one spec file must be ejected")
            for fname in spec_files:
                content = open(os.path.join(tests_dir, fname)).read()
                # Must not import from any cherenkov path
                self.assertNotRegex(
                    content,
                    r"from\s+['\"]cherenkov",
                    f"{fname}: found cherenkov import",
                )
                self.assertNotRegex(
                    content,
                    r"require\s*\(\s*['\"]cherenkov",
                    f"{fname}: found cherenkov require",
                )

    def test_playwright_config_has_no_cherenkov_reference(self):
        """playwright.config.ts must be purely standard."""
        with tempfile.TemporaryDirectory() as base:
            out = self._eject(base)
            content = open(os.path.join(out, "playwright.config.ts")).read()
            self.assertNotIn("cherenkov", content.lower())

    def test_audit_detects_injected_lock_in(self):
        """The lock-in auditor must catch a deliberately injected cherenkov reference."""
        with tempfile.TemporaryDirectory() as base:
            out = self._eject(base)
            # Inject a lock-in violation
            bad_file = os.path.join(out, "tests", "poisoned.spec.ts")
            with open(bad_file, "w") as f:
                f.write("import { trace } from 'cherenkov-trace';\n")
            audit = self.engine.audit_lock_in(out)
            self.assertFalse(audit.clean, "Auditor should detect the injected violation")
            self.assertTrue(
                any("poisoned.spec.ts" in v["file"] for v in audit.violations)
            )

    def test_ejected_suite_runs_standalone_npm_check(self):
        """package.json scripts.test must be 'playwright test' — runnable without cherenkov."""
        with tempfile.TemporaryDirectory() as base:
            out = self._eject(base)
            pkg = json.loads(open(os.path.join(out, "package.json")).read())
            test_script = pkg.get("scripts", {}).get("test", "")
            self.assertIn("playwright", test_script.lower())
            self.assertNotIn("cherenkov", test_script.lower())
