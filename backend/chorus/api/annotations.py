"""Read one item and save its label."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from chorus.api.deps import current_user, get_conn
from chorus.db.queries import items
from chorus.services.lists import save_annotation
from chorus.tasks.base import TaskError

router = APIRouter()


class AnnotationBody(BaseModel):
    value: dict
    elapsed_ms: int | None = None


@router.get("/items/{item_id}")
def get_item(
    item_id: str,
    user: dict = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del user
    item = items.get_item(conn, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/items/{item_id}/annotation")
def put_annotation(
    item_id: str,
    body: AnnotationBody,
    user: dict = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        return save_annotation(
            conn,
            user_id=user["id"],
            item_id=item_id,
            value=body.value,
            elapsed_ms=body.elapsed_ms,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Item not found") from exc
    except TaskError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
