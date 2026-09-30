"""Per-user partition progress: todo or done."""

from __future__ import annotations

import sqlite3

from chorus.db.connection import utcnow
from chorus.db.queries.common import row_dict


def get_progress(conn: sqlite3.Connection, user_id: str, partition_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT * FROM partition_progress
        WHERE user_id = ? AND partition_id = ?
        """,
        (user_id, partition_id),
    ).fetchone()
    return row_dict(row)


def set_progress(
    conn: sqlite3.Connection,
    user_id: str,
    partition_id: str,
    status: str,
    done_via: str | None,
) -> dict:
    now = utcnow()
    existing = get_progress(conn, user_id, partition_id)
    if existing is None:
        conn.execute(
            """
            INSERT INTO partition_progress
              (user_id, partition_id, status, done_via, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, partition_id, status, done_via, now, now),
        )
    else:
        conn.execute(
            """
            UPDATE partition_progress
            SET status = ?, done_via = ?, updated_at = ?
            WHERE user_id = ? AND partition_id = ?
            """,
            (status, done_via, now, user_id, partition_id),
        )
    conn.commit()
    progress = get_progress(conn, user_id, partition_id)
    assert progress is not None
    return progress


def progress_for_partition(conn: sqlite3.Connection, partition_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM partition_progress WHERE partition_id = ?",
        (partition_id,),
    ).fetchall()
    return [row_dict(row) for row in rows]  # type: ignore[misc]
