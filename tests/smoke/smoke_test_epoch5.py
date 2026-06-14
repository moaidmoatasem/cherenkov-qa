"""
smoke_test_epoch5.py — Epoch 5 (Experience + Configuration) smoke tests.
Authority: v3.1 + delta. Tests init, doctor, dashboard, and layered config.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestConfigLoader(unittest.TestCase):
    """Test the layered config resolution (E5-2)."""

    def setUp(self):
        from cherenkov.core.config_loader import LayeredConfig

        self.LayeredConfig = LayeredConfig

    def test_builtin_defaults_loaded(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        self.assertEqual(cfg.get("profile"), "laptop")
        self.assertEqual(cfg.get("substrate.egress"), "internal")
        self.assertEqual(cfg.get("substrate.tiers.small.model"), "qwen2.5-coder:7b")

    def test_profile_overrides(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        cfg.load_profile("frontier-cloud")
        self.assertEqual(cfg.get("substrate.egress"), "any")
        self.assertEqual(cfg.get("substrate.tiers.deep.provider"), "openai")
        self.assertEqual(cfg.get("substrate.budgets.max_cost_usd_per_run"), 5.0)

    def test_profile_enterprise_vpc(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        cfg.load_profile("enterprise-vpc")
        self.assertEqual(cfg.get("substrate.egress"), "none")
        self.assertEqual(cfg.get("continuity.mode"), "daemon")

    def test_profile_ci(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        cfg.load_profile("ci")
        self.assertEqual(cfg.get("substrate.tiers.deep.model"), "qwen2.5-coder:7b")
        self.assertEqual(cfg.get("continuity.behavioral_diff_on_pr"), True)

    def test_unknown_profile_ignored(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        cfg.load_profile("nonexistent")
        # Should remain at defaults
        self.assertEqual(cfg.get("profile"), "laptop")

    def test_cli_override_wins(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        cfg.load_profile("enterprise-vpc")
        cfg.load_cli_override("substrate.egress", "internal")
        self.assertEqual(cfg.get("substrate.egress"), "internal")
        # provenance shows CLI flag won
        prov = cfg.get_with_provenance("substrate.egress")
        self.assertEqual(prov[-1][0], "cli flag")

    def test_unknown_key_errors(self):
        cfg = self.Layeredget_settings()
        cfg.load_cli_override("nonexistent.key", "value")
        self.assertTrue(len(cfg.errors()) > 0)

    def test_to_dict_and_nested(self):
        cfg = self.Layeredget_settings()
        cfg.load_defaults()
        flat = cfg.to_dict()
        self.assertIn("substrate.egress", flat)
        nested = cfg.to_nested_dict()
        self.assertIn("substrate", nested)
        self.assertIn("egress", nested["substrate"])

    def test_autodetect_spec_returns_list(self):
        cfg = self.Layeredget_settings()
        specs = cfg.autodetect_spec()
        self.assertIsInstance(specs, list)

    def test_env_override(self):
        os.environ["CHERENKOV_EGRESS"] = "any"
        try:
            cfg = self.Layeredget_settings()
            cfg.load_defaults()
            cfg.load_env()
            self.assertEqual(cfg.get("substrate.egress"), "any")
            prov = cfg.get_with_provenance("substrate.egress")
            self.assertIn("env:", prov[-1][0])
        finally:
            del os.environ["CHERENKOV_EGRESS"]


class TestInitCommand(unittest.TestCase):
    """Test the init command logic (E5-1)."""

    def test_generate_toml_contains_profile(self):
        from cherenkov.stages.init_cmd import generate_toml

        toml = generate_toml(spec_files=[], profile="laptop")
        self.assertIn('profile = "laptop"', toml)

    def test_generate_toml_with_specs(self):
        from cherenkov.stages.init_cmd import generate_toml

        toml = generate_toml(spec_files=["openapi.yaml", "spec.json"], profile="ci")
        self.assertIn('"openapi.yaml"', toml)
        self.assertIn('"spec.json"', toml)
        self.assertIn('profile = "ci"', toml)

    def test_generate_toml_is_valid_toml(self):
        from cherenkov.stages.init_cmd import generate_toml

        toml = generate_toml(spec_files=["stub/target_spec.json"], profile="laptop")
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                self.skipTest("tomllib/tomli not available")
        parsed = tomllib.loads(toml)
        self.assertEqual(parsed["profile"], "laptop")
        self.assertIn("sources", parsed)
        self.assertIn("substrate", parsed)
        self.assertIn("divergence", parsed)

    def test_init_writes_file(self):
        from cherenkov.stages.init_cmd import run_init

        cwd = Path.cwd()
        toml_path = cwd / "cherenkov.toml"
        backup = None
        if toml_path.exists():
            backup = toml_path.read_text(encoding="utf-8")
        try:
            rc = run_init()
            self.assertEqual(rc, 0)
            self.assertTrue(toml_path.exists())
            content = toml_path.read_text(encoding="utf-8")
            self.assertIn("profile", content)
        finally:
            if backup is not None:
                toml_path.write_text(backup, encoding="utf-8")
            elif toml_path.exists():
                toml_path.unlink()


class TestDoctorCommand(unittest.TestCase):
    """Test the doctor command logic (E5-3)."""

    def test_doctor_runs_without_error(self):
        from cherenkov.stages.doctor_cmd import run_doctor

        try:
            rc = run_doctor()
            self.assertIn(rc, (0, 1))
        except Exception as e:
            self.fail(f"doctor raised unexpected exception: {e}")

    def test_check_ollama_binary(self):
        from cherenkov.stages.doctor_cmd import check_ollama_binary

        ok, detail = check_ollama_binary()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(detail, str)

    def test_check_node(self):
        from cherenkov.stages.doctor_cmd import check_node

        ok, detail = check_node()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(detail, str)

    def test_check_egress_blocked(self):
        from cherenkov.core.config_loader import LayeredConfig
        from cherenkov.stages.doctor_cmd import check_egress_blocked

        cfg = Layeredget_settings()
        cfg.load_defaults()
        healthy, detail = check_egress_blocked(cfg)
        self.assertIsInstance(healthy, bool)
        self.assertIsInstance(detail, str)


class TestDashboardCommand(unittest.TestCase):
    """Test the dashboard command logic (E5-4)."""

    def test_dashboard_runs_without_error(self):
        from cherenkov.dashboard.render import run_dashboard

        try:
            rc = run_dashboard()
            self.assertEqual(rc, 0)
        except Exception as e:
            self.fail(f"dashboard raised unexpected exception: {e}")

    def test_mock_data_renders(self):
        from cherenkov.dashboard.render import render_dashboard

        output = render_dashboard()
        self.assertIn("Truth Model", output)
        self.assertIn("Open Divergences", output)
        self.assertIn("POST /users", output)
        self.assertIn("D1_spec_code", output)

    def test_mock_truth_model(self):
        from cherenkov.dashboard.render import render_truth_model

        output = render_truth_model()
        self.assertIn("Claim Graph", output)
        self.assertIn("POST /users", output)


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration of new commands."""

    def test_init_subcommand_in_help(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("cherenkov_cli", "cherenkov.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        parser = mod.get_parser()
        help_text = parser.format_help()
        self.assertIn("init", help_text)
        self.assertIn("doctor", help_text)
        self.assertIn("dashboard", help_text)

    def test_init_help_contains_profile(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("cherenkov_cli", "cherenkov.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        parser = mod.get_parser()
        init_parser = None
        for action in parser._actions:
            if (
                hasattr(action, "choices")
                and action.choices
                and "init" in action.choices
            ):
                init_parser = action.choices["init"]
                break
        self.assertIsNotNone(init_parser)
        help_text = init_parser.format_help()
        self.assertIn("--profile", help_text)
        self.assertIn("--force", help_text)


if __name__ == "__main__":
    unittest.main()
