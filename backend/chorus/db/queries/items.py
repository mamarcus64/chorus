"""Item rows. The id is derived from the partition and the locator."""

from __future__ import annotations

import sqlite3

from chorus.db.connection import utcnow
from chorus.db.ids import item_id as make_item_id
from chorus.db.queries.common import dumps, loads, row_dict


def _public(row: dict | None) -> dict | None:
    if row is None:
        return None
    row["locator"] = loads(row["locator"], {})
    row["features"] = loads(row["features"], {})
    return row


def upsert_item(
    conn: sqlite3.Connection,
    *,
    partition_id: str,
    ordinal: int,
    kind: str,
    locator: dict,
    features: dict,
) -> dict:
    iid = make_item_id(partition_id, locator)
    now = utcnow()
    existing = conn.execute("SELECT id, created_at FROM items WHERE id = ?", (iid,)).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO items
              (id, partition_id, ordinal, kind, locator, features, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (iid, partition_id, ordinal, kind, dumps(locator), dumps(features), now, now),
        )
    else:
        conn.execute(
            """
            UPDATE items
            SET ordinal = ?, kind = ?, locator = ?, features = ?, updated_at = ?
            WHERE id = ?
            """,
            (ordinal, kind, dumps(locator), dumps(features), now, iid),
        )
    conn.commit()
    item = get_item(conn, iid)
    assert item is not None
    return item


def get_item(conn: sqlite3.Connection, item_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return _public(row_dict(row))


def list_items(conn: sqlite3.Connection, partition_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM items WHERE partition_id = ? ORDER BY ordinal",
        (partition_id,),
    ).fetchall()
    return [_public(row_dict(row)) for row in rows]  # type: ignore[misc]


def count_items(conn: sqlite3.Connection, partition_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM items WHERE partition_id = ?",
        (partition_id,),
    ).fetchone()
    return int(row["n"])


def item_ids(conn: sqlite3.Connection, partition_id: str) -> set[str]:
    rows = conn.execute(
        "SELECT id FROM items WHERE partition_id = ?",
        (partition_id,),
    ).fetchall()
    return {row["id"] for row in rows}


def bump_ordinals(conn: sqlite3.Connection, partition_id: str) -> None:
    """Move current ordinals out of the way so a rebuild can reuse 0..n-1."""
    rows = conn.execute(
        "SELECT id FROM items WHERE partition_id = ? ORDER BY ordinal",
        (partition_id,),
    ).fetchall()
    now = utcnow()
    for index, row in enumerate(rows):
        conn.execute(
            "UPDATE items SET ordinal = ?, updated_at = ? WHERE id = ?",
            (1_000_000 + index, now, row["id"]),
        )
    conn.commit()


def items_with_answers(conn: sqlite3.Connection, partition_id: str, user_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT i.*, a.value AS answer_value, a.elapsed_ms AS answer_elapsed_ms
        FROM items i
        LEFT JOIN annotations a ON a.item_id = i.id AND a.user_id = ?
        WHERE i.partition_id = ?
        ORDER BY i.ordinal
        """,
        (user_id, partition_id),
    ).fetchall()
    out = []
    for row in rows:
        item = row_dict(row)
        assert item is not None
        item["locator"] = loads(item["locator"], {})
        item["features"] = loads(item["features"], {})
        raw = item.pop("answer_value")
        item["answer"] = loads(raw, None) if raw else None
        out.append(item)
    return out
