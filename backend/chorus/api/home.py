"""The three home-page lists."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from chorus.api.deps import current_user, get_conn
from chorus.services.lists import home as home_lists

router = APIRouter()


@router.get("/home")
def home(
    user: dict = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    return home_lists(conn, user["id"])
