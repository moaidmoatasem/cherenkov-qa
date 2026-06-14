"""Tests for E2-4: Traffic adapter (HAR parser)."""

import unittest
import json
import tempfile
import os

from cherenkov.truth.sources.traffic import TrafficSourceAdapter


class TestTrafficSourceAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = TrafficSourceAdapter()

    def _write_har(self, entries: list[dict]) -> str:
        har = {
            "log": {
                "version": "1.2",
                "entries": entries,
            }
        }
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".har", delete=False, encoding="utf-8"
        )
        json.dump(har, tmp)
        tmp.close()
        return tmp.name

    def test_adapter_implements_interface(self):
        from cherenkov.truth.sources.interface import SourceAdapter

        self.assertIsInstance(self.adapter, SourceAdapter)

    def test_discover_claims_raises_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            self.adapter.discover_claims("/nonexistent/file.har")

    def test_discover_claims_empty_har(self):
        path = self._write_har([])
        try:
            claims = self.adapter.discover_claims(path)
            self.assertEqual(claims, [])
        finally:
            os.unlink(path)

    def test_discover_claims_extracts_status(self):
        entry = {
            "request": {"method": "GET", "url": "http://example.com/api/users"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {"send": 5, "wait": 20, "receive": 10},
        }
        path = self._write_har([entry])
        try:
            claims = self.adapter.discover_claims(path)
            self.assertTrue(any(c.category == "observed_status" for c in claims))
            status_claim = [c for c in claims if c.category == "observed_status"][0]
            self.assertEqual(status_claim.value["status"], 200)
            self.assertIn("GET http://example.com/api/users", status_claim.subject)
        finally:
            os.unlink(path)

    def test_discover_claims_extracts_latency(self):
        entry = {
            "request": {"method": "POST", "url": "http://example.com/api/users"},
            "response": {"status": 201, "statusText": "Created", "headers": []},
            "timings": {"send": 10, "wait": 50, "receive": 15},
        }
        path = self._write_har([entry])
        try:
            claims = self.adapter.discover_claims(path)
            latency_claims = [c for c in claims if c.category == "observed_latency"]
            self.assertEqual(len(latency_claims), 1)
            self.assertEqual(latency_claims[0].value["total_ms"], 75)
        finally:
            os.unlink(path)

    def test_discover_claims_extracts_headers(self):
        entry = {
            "request": {"method": "GET", "url": "http://example.com/api/data"},
            "response": {
                "status": 200,
                "statusText": "OK",
                "headers": [{"name": "Content-Type", "value": "application/json"}],
            },
            "timings": {},
        }
        path = self._write_har([entry])
        try:
            claims = self.adapter.discover_claims(path)
            header_claims = [c for c in claims if c.category == "observed_headers"]
            self.assertEqual(len(header_claims), 1)
            self.assertEqual(
                header_claims[0].value.get("Content-Type"), "application/json"
            )
        finally:
            os.unlink(path)

    def test_discover_claims_provenance_is_traffic(self):
        from cherenkov.core.contracts import ProvenanceType

        entry = {
            "request": {"method": "GET", "url": "http://example.com/health"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {},
        }
        path = self._write_har([entry])
        try:
            claims = self.adapter.discover_claims(path)
            for c in claims:
                self.assertEqual(c.provenance.source_type, ProvenanceType.TRAFFIC)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
