"""Tests for VectorStore protocol and SqliteVecStore implementation."""

from palimpsest.vectorstore.protocol import VectorStore
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore


class TestSqliteVecStore:
    def test_protocol_conformance(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        assert isinstance(store, VectorStore)
        store.close()

    def test_add_and_count(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        store.add(["a"], [[0.1, 0.2, 0.3, 0.4]])
        assert store.count() == 1
        store.close()

    def test_add_multiple(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        store.add(
            ["a", "b", "c"],
            [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8], [0.9, 1.0, 0.1, 0.2]],
            [{"para_index": 0}, {"para_index": 1}, {"para_index": 2}],
        )
        assert store.count() == 3
        store.close()

    def test_search(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        store.add(
            ["a", "b"],
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        )
        results = store.search([1.0, 0.0, 0.0, 0.0], k=1)
        assert len(results) == 1
        assert results[0][0] == "a"
        store.close()

    def test_delete(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        store.add(["a", "b"], [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]])
        assert store.count() == 2
        store.delete(["a"])
        assert store.count() == 1
        store.close()

    def test_max_stored_index_empty(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        assert store.max_stored_index() == -1
        store.close()

    def test_max_stored_index_after_add(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        store.add(
            ["p:0", "p:1", "p:2"],
            [[0.1] * 4, [0.2] * 4, [0.3] * 4],
            [{"para_index": 0}, {"para_index": 1}, {"para_index": 2}],
        )
        assert store.max_stored_index() == 2
        store.close()

    def test_get_all_vectors(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        vecs = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
        store.add(
            ["p:0", "p:1"],
            vecs,
            [{"para_index": 0}, {"para_index": 1}],
        )
        result = store.get_all_vectors()
        assert len(result) == 2
        assert len(result[0]) == 4
        assert abs(result[0][0] - 0.1) < 0.01
        store.close()

    def test_idempotent_embed(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4)
        store.add(
            ["p:0"],
            [[0.1, 0.2, 0.3, 0.4]],
            [{"para_index": 0}],
        )
        watermark = store.max_stored_index()
        assert watermark == 0
        # Simulating second call: nothing with index > 0 to add
        store.close()

    def test_wal_mode(self, tmp_path):
        store = SqliteVecStore(tmp_path / "test.db", dim=4, wal=True)
        store.add(["a"], [[0.1, 0.2, 0.3, 0.4]])
        # Open second connection to verify WAL allows concurrent reads
        import sqlite3
        conn2 = sqlite3.connect(str(tmp_path / "test.db"))
        row = conn2.execute("SELECT COUNT(*) FROM vec_meta").fetchone()
        assert row[0] == 1
        conn2.close()
        store.close()
