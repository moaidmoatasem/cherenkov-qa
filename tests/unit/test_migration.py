import os
import tempfile
import pytest
from cherenkov.core.migration import SchemaMigration


@pytest.fixture
def db_path():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = tmp.name
    tmp.close()
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_needs_migration_fresh(db_path):
    sm = SchemaMigration(db_path, current_version=0, target_version=1)
    assert sm.needs_migration()


def test_needs_migration_up_to_date(db_path):
    sm = SchemaMigration(db_path, current_version=0, target_version=1)
    sm.apply([(1, "CREATE TABLE IF NOT EXISTS t (id INT)")])
    sm2 = SchemaMigration(db_path, current_version=1, target_version=1)
    assert not sm2.needs_migration()


def test_apply_migration(db_path):
    sm = SchemaMigration(db_path, current_version=0, target_version=1)
    result = sm.apply([(1, "CREATE TABLE IF NOT EXISTS test_table (id INT)")])
    assert result


def test_get_applied_version(db_path):
    sm = SchemaMigration(db_path, current_version=0, target_version=1)
    assert sm.get_applied_version() == 0
    sm.apply([(1, "CREATE TABLE IF NOT EXISTS t1 (id INT)")])
    assert sm.get_applied_version() == 1


def test_apply_multiple(db_path):
    sm = SchemaMigration(db_path, current_version=0, target_version=2)
    result = sm.apply([
        (1, "CREATE TABLE IF NOT EXISTS t1 (id INT)"),
        (2, "CREATE TABLE IF NOT EXISTS t2 (id INT)"),
    ])
    assert result
    assert sm.get_applied_version() == 2
