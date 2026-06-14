"""Tests for E2-5: DB-schema adapter."""

import unittest
import tempfile
import os

from cherenkov.truth.sources.db_schema import DBSchemaSourceAdapter, _parse_create_table


class TestParseCreateTable(unittest.TestCase):
    def test_parse_simple_table(self):
        sql = "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT);"
        tables = _parse_create_table(sql)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["name"], "users")
        self.assertEqual(len(tables[0]["columns"]), 3)
        self.assertEqual(tables[0]["columns"][0]["name"], "id")
        self.assertEqual(tables[0]["columns"][0]["primary_key"], True)
        self.assertEqual(tables[0]["columns"][1]["name"], "name")
        self.assertEqual(tables[0]["columns"][1]["nullable"], False)

    def test_parse_multiple_tables(self):
        sql = (
            "CREATE TABLE users (id INTEGER);\n"
            "CREATE TABLE posts (id INTEGER, title TEXT);\n"
        )
        tables = _parse_create_table(sql)
        self.assertEqual(len(tables), 2)

    def test_parse_empty_string(self):
        tables = _parse_create_table("")
        self.assertEqual(tables, [])

    def test_parse_with_constraints(self):
        sql = (
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, "
            "user_id INTEGER NOT NULL, "
            "amount REAL DEFAULT 0.0, "
            "FOREIGN KEY (user_id) REFERENCES users(id)"
            ");"
        )
        tables = _parse_create_table(sql)
        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0]["constraints"]), 1)
        self.assertEqual(tables[0]["constraints"][0]["type"], "FOREIGN")

    def test_parse_with_if_not_exists(self):
        sql = "CREATE TABLE IF NOT EXISTS users (id INTEGER);"
        tables = _parse_create_table(sql)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["name"], "users")


class TestDBSchemaSourceAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = DBSchemaSourceAdapter()

    def _write_schema(self, sql: str) -> str:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", delete=False, encoding="utf-8"
        )
        tmp.write(sql)
        tmp.close()
        return tmp.name

    def test_adapter_implements_interface(self):
        from cherenkov.truth.sources.interface import SourceAdapter

        self.assertIsInstance(self.adapter, SourceAdapter)

    def test_discover_claims_raises_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            self.adapter.discover_claims("/nonexistent/schema.sql")

    def test_discover_claims_empty_file(self):
        path = self._write_schema("")
        try:
            claims = self.adapter.discover_claims(path)
            self.assertEqual(claims, [])
        finally:
            os.unlink(path)

    def test_discover_claims_extracts_table(self):
        path = self._write_schema("CREATE TABLE users (id INTEGER);")
        try:
            claims = self.adapter.discover_claims(path)
            table_claims = [c for c in claims if c.category == "table"]
            self.assertEqual(len(table_claims), 1)
            self.assertEqual(table_claims[0].value["name"], "users")
        finally:
            os.unlink(path)

    def test_discover_claims_extracts_columns(self):
        path = self._write_schema(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);"
        )
        try:
            claims = self.adapter.discover_claims(path)
            col_claims = [c for c in claims if c.category == "column"]
            self.assertEqual(len(col_claims), 2)
            id_col = [c for c in col_claims if c.value["name"] == "id"][0]
            self.assertTrue(id_col.value["primary_key"])
            name_col = [c for c in col_claims if c.value["name"] == "name"][0]
            self.assertFalse(name_col.value["nullable"])
        finally:
            os.unlink(path)

    def test_discover_claims_provenance_is_db(self):
        from cherenkov.core.contracts import ProvenanceType

        path = self._write_schema("CREATE TABLE items (id INTEGER);")
        try:
            claims = self.adapter.discover_claims(path)
            for c in claims:
                self.assertEqual(c.provenance.source_type, ProvenanceType.DB)
        finally:
            os.unlink(path)

    def test_discover_claims_extracts_default(self):
        path = self._write_schema(
            "CREATE TABLE config (key TEXT, value TEXT DEFAULT 'active');"
        )
        try:
            claims = self.adapter.discover_claims(path)
            col_claims = [c for c in claims if c.category == "column"]
            value_col = [c for c in col_claims if c.value["name"] == "value"][0]
            self.assertEqual(value_col.value["default"], "'active'")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
