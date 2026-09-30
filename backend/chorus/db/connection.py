"""SQLite connection for one project database."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from chorus.config import settings


def utcnow() -> str:
    """ISO-8601 UTC with milliseconds. Lexicographic order matches time order."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def connect(project: str) -> sqlite3.Connection:
    path = settings().db_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def checkpoint(project: str) -> None:
    path = settings().db_path(project)
    if not path.exists():
        return
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
