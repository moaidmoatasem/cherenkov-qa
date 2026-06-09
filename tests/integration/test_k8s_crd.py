"""Lightweight wrapper: K8s CRD structure tests."""
import unittest
from tests.integration.test_k8s_operator import TestK8sCRDStructure

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestK8sCRDStructure)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
