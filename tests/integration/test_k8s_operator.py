"""Integration tests for K8s operator — validates operator logic without a live cluster."""
import unittest
from unittest import mock


class TestConformanceCheckOperatorConfig(unittest.TestCase):
    """Verify K8s operator RBAC and CRD config files are well-formed."""

    def test_rbac_role_yaml_exists_and_valid(self):
        import yaml, os
        rbac_candidates = [
            "operator/config/rbac/role.yaml",
            "operator/config/rbac/manager_role.yaml",
        ]
        found = [p for p in rbac_candidates if os.path.exists(p)]
        self.assertTrue(found, "RBAC role.yaml not found")
        with open(found[0]) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["kind"], "ClusterRole")
        rules = data.get("rules", [])
        api_groups = [r.get("apiGroups", []) for r in rules]
        all_groups = [g for groups in api_groups for g in groups]
        self.assertIn("cherenkov.io", all_groups, "Missing cherenkov.io RBAC rule")
        self.assertIn("batch", all_groups, "Missing batch RBAC rule")

    def test_crd_yaml_exists_and_valid(self):
        import yaml, os, glob
        crds = glob.glob("operator/config/crd/bases/*.yaml")
        self.assertTrue(crds, "No CRD YAML files found")
        with open(crds[0]) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["kind"], "CustomResourceDefinition")
        self.assertIn("cherenkov.io", data["metadata"]["name"])


class TestK8sCRDStructure(unittest.TestCase):
    """Verify the CRD types file has the required fields."""

    def test_types_file_has_device_targets(self):
        import os
        types_file = "operator/api/v1alpha1/conformancecheck_types.go"
        if not os.path.exists(types_file):
            self.skipTest("types file not found")
        with open(types_file) as f:
            content = f.read()
        self.assertIn("DeviceTargets", content)
        self.assertIn("VisualConfig", content)
        self.assertIn("TestResult", content)

    def test_controller_passes_device_env_vars(self):
        import os
        ctrl = "operator/controllers/conformancecheck_controller.go"
        if not os.path.exists(ctrl):
            self.skipTest("controller file not found")
        with open(ctrl) as f:
            content = f.read()
        self.assertIn("CHERENKOV_DEVICE_TARGETS", content)
        self.assertIn("CHERENKOV_VLM_TIER", content)


if __name__ == "__main__":
    unittest.main()
