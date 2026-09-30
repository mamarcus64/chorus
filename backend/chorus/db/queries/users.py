"""User rows."""

from __future__ import annotations

import sqlite3
import uuid

from chorus.db.connection import utcnow
from chorus.db.queries.common import row_dict


def create_user(conn: sqlite3.Connection, username: str, password_hash: str) -> dict:
    now = utcnow()
    user_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (id, username, password_hash, is_admin, created_at, updated_at)
        VALUES (?, ?, ?, 0, ?, ?)
        """,
        (user_id, username, password_hash, now, now),
    )
    conn.commit()
    user = get_user(conn, user_id)
    assert user is not None
    return user


def get_user(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_dict(row)


def get_user_by_username(conn: sqlite3.Connection, username: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
        (username,),
    ).fetchone()
    return row_dict(row)


def list_users(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM users ORDER BY username COLLATE NOCASE").fetchall()
    return [row_dict(row) for row in rows]  # type: ignore[misc]
