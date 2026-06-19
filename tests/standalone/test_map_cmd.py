"""Tests for E2-6: cherenkov map command."""

import unittest
import os

from cherenkov.core.truth_model import TruthModel
from cherenkov.stages.map_cmd import build_truth_model, render_truth_model


class TestBuildTruthModel(unittest.TestCase):
    def test_build_from_openapi(self):
        # Use absolute path to stripe_spec.json
        stripe_spec_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "stripe_spec.json"
        )
        sources = {"openapi": [stripe_spec_path]}
        tm = build_truth_model(sources)
        self.assertIsInstance(tm, TruthModel)
        self.assertGreater(len(tm.nodes), 0)
        self.assertGreater(len(tm.edges), 0)
        sources_found = tm.get_sources()
        self.assertGreater(len(sources_found), 0)

    def test_build_from_empty_sources(self):
        tm = build_truth_model({})
        self.assertEqual(len(tm.nodes), 0)

    def test_build_from_nonexistent_file(self):
        sources = {"openapi": ["/nonexistent/spec.yaml"]}
        tm = build_truth_model(sources)
        sources_list = tm.get_sources()
        self.assertEqual(len(sources_list), 1)
        self.assertIn("error", sources_list[0].properties)

    def test_render_empty(self):
        tm = TruthModel()
        output = render_truth_model(tm)
        self.assertIn("CHERENKOV Truth Model", output)
        self.assertIn("Sources:      0", output)
        self.assertIn("Endpoints:    0", output)

    def test_render_with_sources(self):
        # Use absolute path to stripe_spec.json
        stripe_spec_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "stripe_spec.json"
        )
        sources = {"openapi": [stripe_spec_path]}
        tm = build_truth_model(sources)
        output = render_truth_model(tm, detailed=True)
        self.assertIn("CHERENKOV Truth Model", output)
        self.assertIn("Sources:", output)

    def test_render_detailed_shows_provenance(self):
        # Use absolute path to stripe_spec.json
        stripe_spec_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "stripe_spec.json"
        )
        sources = {"openapi": [stripe_spec_path]}
        tm = build_truth_model(sources)
        output = render_truth_model(tm, detailed=True)
        self.assertIn("provenance:", output)


if __name__ == "__main__":
    unittest.main()
