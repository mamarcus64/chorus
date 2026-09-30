"""Human labels. One row per user per item; saving again updates it."""

from __future__ import annotations

import sqlite3

from chorus.db.connection import utcnow
from chorus.db.ids import annotation_id as make_annotation_id
from chorus.db.queries.common import dumps, loads, row_dict


def _public(row: dict | None) -> dict | None:
    if row is None:
        return None
    row["value"] = loads(row["value"], {})
    return row


def upsert_annotation(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    item_id: str,
    value: dict,
    elapsed_ms: int | None,
) -> dict:
    aid = make_annotation_id(user_id, item_id)
    now = utcnow()
    payload = dumps(value)
    existing = conn.execute(
        "SELECT id FROM annotations WHERE user_id = ? AND item_id = ?",
        (user_id, item_id),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO annotations
              (id, user_id, item_id, value, elapsed_ms, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (aid, user_id, item_id, payload, elapsed_ms, now, now),
        )
    else:
        conn.execute(
            """
            UPDATE annotations
            SET value = ?, elapsed_ms = ?, updated_at = ?
            WHERE user_id = ? AND item_id = ?
            """,
            (payload, elapsed_ms, now, user_id, item_id),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM annotations WHERE id = ?", (aid,)).fetchone()
    annotation = _public(row_dict(row))
    assert annotation is not None
    return annotation


def count_for_user_partition(conn: sqlite3.Connection, user_id: str, partition_id: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM annotations a
        JOIN items i ON i.id = a.item_id
        WHERE a.user_id = ? AND i.partition_id = ?
        """,
        (user_id, partition_id),
    ).fetchone()
    return int(row["n"])


def counts_by_user(conn: sqlite3.Connection, partition_id: str) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT a.user_id AS user_id, COUNT(*) AS n
        FROM annotations a
        JOIN items i ON i.id = a.item_id
        WHERE i.partition_id = ?
        GROUP BY a.user_id
        """,
        (partition_id,),
    ).fetchall()
    return {row["user_id"]: int(row["n"]) for row in rows}
