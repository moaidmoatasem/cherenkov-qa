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
            pkg = json.loads(open(os.path.join(out, "package.json")).read())  # noqa: SIM115
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
            content = open(os.path.join(out, "client.ts")).read()  # noqa: SIM115
            self.assertNotIn("cherenkov", content.lower())


class TestEjectCustomTestsDir(unittest.TestCase):
    """Regression: eject hardcoded stub/generated_tests and ignored any custom
    --output-dir `cherenkov generate` was given, silently ejecting unrelated
    tracked fixtures instead of the user's own generated tests while still
    reporting success. `tests_src_dir` lets a caller point eject at wherever
    generate actually wrote its output."""

    def test_custom_tests_src_dir_is_used_instead_of_default(self):
        from cherenkov.execution.eject import EjectorEngine

        with tempfile.TemporaryDirectory() as custom_src, tempfile.TemporaryDirectory() as base:
            spec_path = os.path.join(custom_src, "my_own_scenario.spec.ts")
            with open(spec_path, "w") as f:
                f.write("import { test, expect } from '@playwright/test';\n")

            engine = EjectorEngine(run_id="test-run", tests_src_dir=custom_src)
            self.assertEqual(engine.tests_src_dir, custom_src)

            out = os.path.join(base, "ejected")
            result = engine.eject_suite(out)

            self.assertTrue(result)
            ejected_file = os.path.join(out, "tests", "my_own_scenario.spec.ts")
            self.assertTrue(
                os.path.exists(ejected_file),
                "eject must read from the custom tests_src_dir, not the hardcoded default",
            )

    def test_default_tests_src_dir_unchanged_when_not_overridden(self):
        from cherenkov.execution.eject import EjectorEngine

        default_engine = EjectorEngine(run_id="test-run")
        expected = os.path.join(default_engine.stub_dir, "generated_tests")
        self.assertEqual(default_engine.tests_src_dir, expected)

    def test_cli_eject_tests_dir_flag_is_wired_through(self):
        """End-to-end: `cherenkov eject --tests-dir <custom>` (the CLI flag,
        not just the engine constructor) must actually read from <custom>,
        matching the documented `generate --output-dir <custom>` combo in
        docs/GETTING_STARTED.md."""
        from click.testing import CliRunner

        from cherenkov.cli.commands.simple import eject_cmd

        with tempfile.TemporaryDirectory() as custom_src, tempfile.TemporaryDirectory() as base:
            spec_path = os.path.join(custom_src, "my_own_scenario.spec.ts")
            with open(spec_path, "w") as f:
                f.write("import { test, expect } from '@playwright/test';\n")

            out = os.path.join(base, "ejected")
            runner = CliRunner()
            result = runner.invoke(
                eject_cmd, ["--output", out, "--tests-dir", custom_src]
            )

            self.assertEqual(result.exit_code, 0, result.output)
            ejected_file = os.path.join(out, "tests", "my_own_scenario.spec.ts")
            self.assertTrue(
                os.path.exists(ejected_file),
                "CLI --tests-dir flag must be threaded through to EjectorEngine",
            )
            self.assertIn(custom_src, result.output)

    def test_cli_eject_rejects_nonexistent_tests_dir(self):
        """A typo'd --tests-dir should fail loudly, not silently fall back to
        unrelated tracked fixtures."""
        from click.testing import CliRunner

        from cherenkov.cli.commands.simple import eject_cmd

        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "ejected")
            runner = CliRunner()
            result = runner.invoke(
                eject_cmd, ["--output", out, "--tests-dir", "/no/such/dir"]
            )
            self.assertNotEqual(result.exit_code, 0)
