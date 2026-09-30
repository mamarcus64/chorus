"""Task rows. The id is derived from the task name."""

from __future__ import annotations

import sqlite3

from chorus.db.connection import utcnow
from chorus.db.ids import task_id
from chorus.db.queries.common import dumps, loads, row_dict


def _public(row: dict | None) -> dict | None:
    if row is None:
        return None
    row["config"] = loads(row["config"], {})
    return row


def upsert_task(
    conn: sqlite3.Connection,
    *,
    name: str,
    code_key: str,
    code_version: int,
    config: dict,
) -> dict:
    tid = task_id(name)
    now = utcnow()
    payload = dumps(config)
    existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (tid,)).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO tasks
              (id, code_key, code_version, name, config, archived_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (tid, code_key, code_version, name, payload, now, now),
        )
    else:
        conn.execute(
            """
            UPDATE tasks
            SET code_key = ?, code_version = ?, config = ?, updated_at = ?
            WHERE id = ?
            """,
            (code_key, code_version, payload, now, tid),
        )
    conn.commit()
    task = get_task(conn, tid)
    assert task is not None
    return task


def get_task(conn: sqlite3.Connection, task_id_: str) -> dict | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id_,)).fetchone()
    return _public(row_dict(row))
