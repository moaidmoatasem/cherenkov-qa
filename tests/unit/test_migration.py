import os
import tempfile
import unittest
from cherenkov.core.migration import SchemaMigration


class TestSchemaMigration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_needs_migration_fresh(self):
        sm = SchemaMigration(self.db_path, current_version=0, target_version=1)
        self.assertTrue(sm.needs_migration())

    def test_needs_migration_up_to_date(self):
        sm = SchemaMigration(self.db_path, current_version=0, target_version=1)
        sm.apply([(1, "CREATE TABLE IF NOT EXISTS t (id INT)")])
        sm2 = SchemaMigration(self.db_path, current_version=1, target_version=1)
        self.assertFalse(sm2.needs_migration())

    def test_apply_migration(self):
        sm = SchemaMigration(self.db_path, current_version=0, target_version=1)
        result = sm.apply([(1, "CREATE TABLE IF NOT EXISTS test_table (id INT)")])
        self.assertTrue(result)

    def test_get_applied_version(self):
        sm = SchemaMigration(self.db_path, current_version=0, target_version=1)
        self.assertEqual(sm.get_applied_version(), 0)
        sm.apply([(1, "CREATE TABLE IF NOT EXISTS t1 (id INT)")])
        self.assertEqual(sm.get_applied_version(), 1)

    def test_apply_multiple(self):
        sm = SchemaMigration(self.db_path, current_version=0, target_version=2)
        result = sm.apply([
            (1, "CREATE TABLE IF NOT EXISTS t1 (id INT)"),
            (2, "CREATE TABLE IF NOT EXISTS t2 (id INT)"),
        ])
        self.assertTrue(result)
        self.assertEqual(sm.get_applied_version(), 2)
