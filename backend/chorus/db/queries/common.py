"""Row and JSON helpers shared by the query modules. No SQL of its own."""

from __future__ import annotations

import json
import sqlite3

from chorus.db.ids import canonical_json


def row_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def loads(value: str | None, default: object) -> object:
    if value is None or value == "":
        return default
    return json.loads(value)


def dumps(value: object) -> str:
    return canonical_json(value)
