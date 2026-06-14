"""Lightweight wrapper: K8s operator config tests (RBAC, CRD, device env vars)."""

import unittest
from tests.integration.test_k8s_operator import TestConformanceCheckOperatorConfig

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestConformanceCheckOperatorConfig)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
