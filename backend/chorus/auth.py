"""Password hashes and the signed session cookie. No SQL."""

from __future__ import annotations

import hmac

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from chorus.config import settings

COOKIE = "chorus_session"
MAX_AGE = 60 * 60 * 24 * 14

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _key_ok(offered: str, expected: str) -> bool:
    if not expected:
        return False
    return hmac.compare_digest(offered, expected)


def registration_key_ok(offered: str) -> bool:
    return _key_ok(offered, settings().registration_key)


def admin_key_ok(offered: str) -> bool:
    return _key_ok(offered, settings().admin_key)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings().secret_key, salt="chorus-session")


def dump_session(project: str, user_id: str) -> str:
    return _serializer().dumps({"project": project, "user_id": user_id})


def read_session(token: str) -> dict:
    return _serializer().loads(token, max_age=MAX_AGE)


__all__ = [
    "BadSignature",
    "COOKIE",
    "MAX_AGE",
    "SignatureExpired",
    "admin_key_ok",
    "dump_session",
    "hash_password",
    "read_session",
    "registration_key_ok",
    "verify_password",
]
