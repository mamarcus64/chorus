"""Partition rows, assignee lists, and the home-page join."""

from __future__ import annotations

import sqlite3

from chorus.db.connection import utcnow
from chorus.db.ids import partition_id as make_partition_id
from chorus.db.queries.common import dumps, loads, row_dict


def _public(row: dict | None) -> dict | None:
    if row is None:
        return None
    row["config"] = loads(row["config"], {})
    return row


def upsert_partition(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    name: str,
    description: str | None,
    config: dict,
) -> dict:
    pid = make_partition_id(task_id, name)
    now = utcnow()
    payload = dumps(config)
    existing = conn.execute("SELECT id FROM partitions WHERE id = ?", (pid,)).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO partitions
              (id, task_id, name, description, config, assignment, archived_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'everyone', NULL, ?, ?)
            """,
            (pid, task_id, name, description, payload, now, now),
        )
    else:
        conn.execute(
            """
            UPDATE partitions
            SET description = ?, config = ?, updated_at = ?
            WHERE id = ?
            """,
            (description, payload, now, pid),
        )
    conn.commit()
    partition = get_partition(conn, pid)
    assert partition is not None
    return partition


def get_partition(conn: sqlite3.Connection, partition_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM partitions WHERE id = ?", (partition_id,)).fetchone()
    return _public(row_dict(row))


def set_archived(conn: sqlite3.Connection, partition_id: str, archived: bool) -> dict:
    now = utcnow()
    conn.execute(
        "UPDATE partitions SET archived_at = ?, updated_at = ? WHERE id = ?",
        (now if archived else None, now, partition_id),
    )
    conn.commit()
    partition = get_partition(conn, partition_id)
    if partition is None:
        raise KeyError(partition_id)
    return partition


def set_assignment_mode(conn: sqlite3.Connection, partition_id: str, mode: str) -> None:
    now = utcnow()
    conn.execute(
        "UPDATE partitions SET assignment = ?, updated_at = ? WHERE id = ?",
        (mode, now, partition_id),
    )
    conn.commit()


def replace_assignees(conn: sqlite3.Connection, partition_id: str, user_ids: list[str]) -> None:
    now = utcnow()
    conn.execute("DELETE FROM partition_assignees WHERE partition_id = ?", (partition_id,))
    for user_id in user_ids:
        conn.execute(
            """
            INSERT INTO partition_assignees (partition_id, user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (partition_id, user_id, now, now),
        )
    conn.commit()


def assignee_ids(conn: sqlite3.Connection, partition_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT user_id FROM partition_assignees WHERE partition_id = ? ORDER BY user_id",
        (partition_id,),
    ).fetchall()
    return [row["user_id"] for row in rows]


_HOME_SQL = """
SELECT
  p.id, p.task_id, p.name, p.description, p.assignment, p.archived_at,
  t.name AS task_name, t.code_key, t.config AS task_config,
  (SELECT COUNT(*) FROM items i WHERE i.partition_id = p.id) AS item_count,
  (SELECT COUNT(*) FROM annotations a
     JOIN items i ON i.id = a.item_id
     WHERE i.partition_id = p.id AND a.user_id = ?) AS answered_count,
  pr.status AS progress_status,
  pr.done_via AS done_via,
  EXISTS (
    SELECT 1 FROM partition_assignees pa
    WHERE pa.partition_id = p.id AND pa.user_id = ?
  ) AS is_assignee
FROM partitions p
JOIN tasks t ON t.id = p.task_id
LEFT JOIN partition_progress pr
  ON pr.partition_id = p.id AND pr.user_id = ?
"""


def home_rows(conn: sqlite3.Connection, user_id: str, partition_id: str | None = None) -> list[dict]:
    sql = _HOME_SQL + " WHERE p.archived_at IS NULL AND t.archived_at IS NULL"
    params: list[str] = [user_id, user_id, user_id]
    if partition_id is not None:
        sql += " AND p.id = ?"
        params.append(partition_id)
    sql += " ORDER BY t.name, p.name"
    rows = conn.execute(sql, params).fetchall()
    out = []
    for row in rows:
        item = row_dict(row)
        assert item is not None
        item["task_config"] = loads(item["task_config"], {})
        item["is_assignee"] = bool(item["is_assignee"])
        out.append(item)
    return out


def admin_rows(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT p.*, t.name AS task_name, t.code_key,
          (SELECT COUNT(*) FROM items i WHERE i.partition_id = p.id) AS item_count
        FROM partitions p
        JOIN tasks t ON t.id = p.task_id
        ORDER BY p.archived_at IS NOT NULL, t.name, p.name
        """
    ).fetchall()
    out = []
    for row in rows:
        item = row_dict(row)
        assert item is not None
        item["config"] = loads(item["config"], {})
        out.append(item)
    return out
