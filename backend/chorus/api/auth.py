"""Register, login, logout, and the current user."""

from __future__ import annotations

import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from chorus.api.deps import current_user, get_conn, public_user
from chorus.auth import (
    COOKIE,
    MAX_AGE,
    admin_key_ok,
    dump_session,
    hash_password,
    registration_key_ok,
    verify_password,
)
from chorus.db.queries import users

router = APIRouter()

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class RegisterBody(BaseModel):
    username: str
    password: str
    registration_key: str


class LoginBody(BaseModel):
    username: str
    password: str
    admin_key: str = ""


def _set_session(response: Response, project: str, user_id: str) -> None:
    response.set_cookie(
        COOKIE,
        dump_session(project, user_id),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=MAX_AGE,
        path="/",
    )


def _check_password(password: str) -> None:
    if len(password) < 8 or len(password) > 200:
        raise HTTPException(status_code=400, detail="Password must be 8 to 200 characters")


@router.post("/auth/register")
def register(
    project: str,
    body: RegisterBody,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if not registration_key_ok(body.registration_key):
        raise HTTPException(status_code=403, detail="Registration key is not valid")
    username = body.username.strip()
    if _USERNAME.fullmatch(username) is None:
        raise HTTPException(
            status_code=400,
            detail="Username must be 1-64 characters: letters, digits, _, ., -",
        )
    _check_password(body.password)
    if users.get_user_by_username(conn, username) is not None:
        raise HTTPException(status_code=409, detail="Username is already registered")
    user = users.create_user(conn, username, hash_password(body.password))
    _set_session(response, project, user["id"])
    return public_user(user)


@router.post("/auth/login")
def login(
    project: str,
    body: LoginBody,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
):
    user = users.get_user_by_username(conn, body.username.strip())
    if user is None or not verify_password(user["password_hash"], body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    admin_key = body.admin_key.strip()
    if admin_key:
        if not admin_key_ok(admin_key):
            raise HTTPException(status_code=403, detail="Admin key is not valid")
        if not user["is_admin"]:
            user = users.set_admin(conn, user["id"])
    _set_session(response, project, user["id"])
    return public_user(user)


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return public_user(user)
