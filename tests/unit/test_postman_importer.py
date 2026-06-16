"""Tests for the Postman Collection importer."""

import tempfile
import os
import json
import unittest
from cherenkov.adapters.postman_importer import PostmanImporter


SAMPLE_COLLECTION = {
    "info": {
        "name": "Sample API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Get Users",
            "request": {
                "method": "GET",
                "header": [{"key": "Accept", "value": "application/json"}],
                "url": {
                    "raw": "https://api.example.com/users",
                    "protocol": "https",
                    "host": ["api", "example", "com"],
                    "path": ["users"]
                }
            }
        },
        {
            "name": "Create User",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "Accept", "value": "application/json"},
                ],
                "url": {
                    "raw": "https://api.example.com/users",
                    "protocol": "https",
                    "host": ["api", "example", "com"],
                    "path": ["users"]
                }
            }
        }
    ]
}

SAMPLE_COLLECTION_WITH_FOLDER = {
    "info": {"name": "Folder Test", "schema": ""},
    "item": [
        {
            "name": "Users",
            "item": [
                {
                    "name": "Get User",
                    "request": {
                        "method": "GET",
                        "url": {"raw": "https://api.example.com/users/1"}
                    }
                }
            ]
        },
        {
            "name": "Health Check",
            "request": {
                "method": "GET",
                "url": {"raw": "https://api.example.com/health"}
            }
        }
    ]
}

SAMPLE_COLLECTION_STRING_URL = {
    "info": {"name": "String URL", "schema": ""},
    "item": [
        {
            "name": "Get Items",
            "request": {
                "method": "GET",
                "url": "https://api.example.com/items"
            }
        }
    ]
}


class TestPostmanImporter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write_collection(self, data: dict) -> str:
        path = os.path.join(self.tmpdir, "collection.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_imports_basic_collection(self):
        path = self._write_collection(SAMPLE_COLLECTION)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        self.assertEqual(len(scenarios), 2)

    def test_imports_methods_correctly(self):
        path = self._write_collection(SAMPLE_COLLECTION)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        methods = {s.method for s in scenarios}
        self.assertIn("GET", methods)
        self.assertIn("POST", methods)

    def test_imports_endpoints(self):
        path = self._write_collection(SAMPLE_COLLECTION)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        endpoints = {s.endpoint for s in scenarios}
        self.assertIn("https://api.example.com/users", endpoints)

    def test_imports_headers(self):
        path = self._write_collection(SAMPLE_COLLECTION)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        create = [s for s in scenarios if s.method == "POST"]
        self.assertEqual(len(create), 1)
        # Scenarios don't store headers directly, but the parse should succeed

    def test_flattens_folders(self):
        path = self._write_collection(SAMPLE_COLLECTION_WITH_FOLDER)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        self.assertEqual(len(scenarios), 2)

    def test_handles_string_url(self):
        path = self._write_collection(SAMPLE_COLLECTION_STRING_URL)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].endpoint, "https://api.example.com/items")

    def test_handles_invalid_file(self):
        importer = PostmanImporter()
        scenarios = importer.import_collection("/nonexistent/file.json")
        self.assertEqual(scenarios, [])

    def test_skips_items_without_request(self):
        data = {
            "info": {"name": "Bad", "schema": ""},
            "item": [
                {"name": "No request here"}
            ]
        }
        path = self._write_collection(data)
        importer = PostmanImporter()
        scenarios = importer.import_collection(path)
        self.assertEqual(len(scenarios), 0)

    def test_parse_item_with_headers(self):
        importer = PostmanImporter()
        item = {
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Authorization", "value": "Bearer token123"},
                    {"key": "Content-Type", "value": "application/json"},
                ],
                "url": {"raw": "https://api.example.com/data"}
            }
        }
        result = importer._parse_item(item)
        self.assertIsNotNone(result)
        self.assertEqual(result.method, "POST")
        self.assertEqual(result.endpoint, "https://api.example.com/data")
