"""Request dependencies. SQL stays in the query modules these call."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request

from chorus.auth import COOKIE, BadSignature, SignatureExpired, read_session
from chorus.config import settings
from chorus.db.connection import connect
from chorus.db.queries import users


def get_conn(project: str) -> Iterator[sqlite3.Connection]:
    if project not in settings().projects:
        raise HTTPException(status_code=404, detail="Unknown project")
    if not settings().db_path(project).exists():
        raise HTTPException(status_code=503, detail="Database has not been migrated")
    conn = connect(project)
    try:
        yield conn
    finally:
        conn.close()


def current_user(
    project: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        data = read_session(token)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status_code=401, detail="Login required") from exc
    if data.get("project") != project:
        raise HTTPException(status_code=401, detail="Login required")
    user = users.get_user(conn, data.get("user_id", ""))
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "is_admin": bool(user["is_admin"]),
    }
