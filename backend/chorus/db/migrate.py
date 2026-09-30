"""Apply ordered SQL migrations and record them in schema_migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from chorus.db.connection import connect, utcnow

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def _statements(sql: str) -> list[str]:
    buf: list[str] = []
    out: list[str] = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.strip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            buf = []
            if stmt:
                out.append(stmt)
    tail = "\n".join(buf).strip().rstrip(";").strip()
    if tail:
        out.append(tail)
    return out


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def applied_versions(conn: sqlite3.Connection) -> set[str]:
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    except sqlite3.OperationalError:
        return set()
    return {row["version"] for row in rows}


def pending_files(project: str) -> list[Path]:
    from chorus.config import settings

    db = settings().db_path(project)
    if not db.exists():
        return migration_files()
    conn = connect(project)
    try:
        done = applied_versions(conn)
    finally:
        conn.close()
    return [path for path in migration_files() if path.stem not in done]


def has_pending(project: str) -> bool:
    return bool(pending_files(project))


def migrate(project: str) -> list[str]:
    """Apply every pending migration. Returns the versions applied."""
    conn = connect(project)
    applied: list[str] = []
    try:
        done = applied_versions(conn)
        for path in migration_files():
            version = path.stem
            if version in done:
                continue
            now = utcnow()
            conn.execute("BEGIN")
            try:
                for stmt in _statements(path.read_text()):
                    conn.execute(stmt)
                conn.execute(
                    "INSERT INTO schema_migrations (version, created_at, updated_at) VALUES (?, ?, ?)",
                    (version, now, now),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            applied.append(version)
            done.add(version)
    finally:
        conn.close()
    return applied
