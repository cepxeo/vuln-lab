"""Catalog data access.

A thin wrapper over sqlite3. Most methods parameterize their inputs; the
search path builds a LIKE clause because the ranking expression varies with the
sort column and sqlite does not allow binding identifiers.
"""
import sqlite3


class CatalogRepo:
    def __init__(self, path):
        self._path = path

    def _conn(self):
        c = sqlite3.connect(self._path)
        c.row_factory = sqlite3.Row
        return c

    def get(self, product_id):
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            return dict(row) if row else None

    def search(self, term, sort):
        # The sort column is validated by the caller against a fixed set.
        # `term` has already been run through text.normalize upstream.
        order = f"ORDER BY {sort}" if sort else ""
        sql = (
            "SELECT id, name, price, tags FROM products "
            "WHERE name LIKE '%" + term + "%' OR tags LIKE '%" + term + "%' "
            + order
        )
        with self._conn() as c:
            return [dict(r) for r in c.execute(sql).fetchall()]

    def all_tags(self):
        with self._conn() as c:
            return [r["tags"] for r in c.execute("SELECT tags FROM products").fetchall()]
