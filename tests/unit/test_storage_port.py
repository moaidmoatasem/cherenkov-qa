import tempfile
from pathlib import Path

import pytest

from cherenkov.ports.storage import (
    QueryFilter,
    StorageConfig,
    StoragePort,
    StorageQuery,
    build_limit,
    build_order_by,
    build_where,
)
from cherenkov.adapters.storage.sqlite import SQLiteStorageAdapter


@pytest.fixture
def adapter():
    d = tempfile.mkdtemp()
    cfg = StorageConfig(
        db_path=Path(d) / "test.db",
        namespace="testns",
        enable_fts=True,
        fts_columns=("title", "body"),
    )
    a = SQLiteStorageAdapter(cfg)
    yield a
    a.close()


def test_port_is_abstract():
    with pytest.raises(TypeError):
        StoragePort()  # type: ignore[abstract]


def test_namespace_property(adapter):
    assert adapter.namespace == "testns"


def test_where_helpers():
    where, params = build_where([QueryFilter(column="n", operator=">", value=3)])
    assert where == " WHERE n > ?"
    assert params == [3]
    where, params = build_where([])
    assert where == ""
    assert params == []
    assert build_order_by("created_at", True) == " ORDER BY created_at DESC"
    assert build_order_by("created_at", False) == " ORDER BY created_at ASC"
    limit, lp = build_limit(10, 5)
    assert limit == " LIMIT ? OFFSET ?"
    assert lp == [10, 5]


def test_insert_and_query_by_id(adapter):
    rid = adapter.insert("entries", {"id": "a1", "title": "alpha", "body": "first", "n": 1})
    assert rid == "a1"
    row = adapter.query_by_id("entries", "a1")
    assert row["title"] == "alpha"
    assert row["n"] == 1


def test_insert_generates_id(adapter):
    rid = adapter.insert("entries", {"title": "no id"})
    assert rid
    assert adapter.query_by_id("entries", rid) is not None


def test_upsert_inserts_and_updates(adapter):
    first = adapter.upsert("entries", {"id": "k1", "title": "v1", "body": "b", "n": 1}, "id")
    assert first == "k1"
    second = adapter.upsert("entries", {"id": "k1", "title": "v2", "body": "b", "n": 2}, "id")
    assert second == "k1"
    assert adapter.count("entries", StorageQuery()) == 1
    row = adapter.query_by_id("entries", "k1")
    assert row["title"] == "v2"
    assert row["n"] == 2


def test_query_filters_and_pagination(adapter):
    for i in range(5):
        adapter.insert("entries", {"id": f"r{i}", "title": f"row {i}", "body": "x", "n": i})
    rows = adapter.query("entries", StorageQuery(filters=[QueryFilter(column="n", operator=">", value=2)]))
    assert {r["id"] for r in rows} == {"r3", "r4"}
    rows = adapter.query("entries", StorageQuery(limit=2, offset=0))
    assert len(rows) == 2


def test_query_one(adapter):
    adapter.insert("entries", {"id": "solo", "title": "only", "body": "y", "n": 7})
    row = adapter.query_one("entries", StorageQuery(filters=[QueryFilter(column="title", operator="=", value="only")]))
    assert row and row["id"] == "solo"


def test_exists_and_count(adapter):
    adapter.insert("entries", {"id": "e1", "title": "t", "body": "b", "n": 1})
    q = StorageQuery(filters=[QueryFilter(column="n", operator="=", value=1)])
    assert adapter.exists("entries", q) is True
    assert adapter.exists("entries", StorageQuery(filters=[QueryFilter(column="n", operator="=", value=999)])) is False
    assert adapter.count("entries", StorageQuery()) == 1
    assert adapter.count("entries", StorageQuery(filters=[QueryFilter(column="n", operator="=", value=999)])) == 0


def test_soft_delete_excludes_row(adapter):
    adapter.insert("entries", {"id": "sd1", "title": "gone", "body": "soon", "n": 5})
    assert adapter.soft_delete("entries", "sd1") == 1
    assert adapter.query_by_id("entries", "sd1") is None
    assert adapter.exists("entries", StorageQuery(filters=[QueryFilter(column="id", operator="=", value="sd1")])) is False
    assert adapter.count("entries", StorageQuery()) == 0
    # hard delete of an already soft-deleted row is a no-op for soft_delete
    assert adapter.soft_delete("entries", "sd1") == 0


def test_delete_hard(adapter):
    adapter.insert("entries", {"id": "hd1", "title": "bye", "body": "b", "n": 3})
    n = adapter.delete("entries", StorageQuery(filters=[QueryFilter(column="n", operator="=", value=3)]))
    assert n == 1
    assert adapter.query_by_id("entries", "hd1") is None


def test_transaction_commit(adapter):
    with adapter.transaction():
        adapter.insert("entries", {"id": "tx1", "title": "a", "body": "b", "n": 1})
    assert adapter.query_by_id("entries", "tx1") is not None


def test_transaction_rollback(adapter):
    with pytest.raises(RuntimeError):
        with adapter.transaction():
            adapter.insert("entries", {"id": "tx2", "title": "a", "body": "b", "n": 2})
            raise RuntimeError("boom")
    assert adapter.query_by_id("entries", "tx2") is None


def test_fts_search(adapter):
    adapter.insert("entries", {"id": "f1", "title": "apples", "body": "green fruit", "n": 1})
    adapter.insert("entries", {"id": "f2", "title": "bananas", "body": "yellow fruit", "n": 2})
    res = adapter.execute(
        "SELECT id FROM testns_entries WHERE rowid IN "
        "(SELECT rowid FROM testns_fts_index WHERE testns_fts_index MATCH ?)",
        ("bananas",),
    )
    assert [r["id"] for r in res] == ["f2"]


def test_execute_raw(adapter):
    adapter.insert("entries", {"id": "raw1", "title": "raw", "body": "data", "n": 9})
    res = adapter.execute(
        "SELECT json_extract(data, '$.title') AS title FROM testns_entries WHERE id = ?", ("raw1",)
    )
    assert res and res[0]["title"] == "raw"
