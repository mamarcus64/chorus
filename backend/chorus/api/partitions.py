"""Open a partition, mark it done, or reopen it."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from chorus.api.deps import current_user, get_conn
from chorus.db.queries import items, partitions, progress, tasks
from chorus.services.lists import mark_done, reopen

router = APIRouter()


def _visible(conn: sqlite3.Connection, partition_id: str) -> dict:
    partition = partitions.get_partition(conn, partition_id)
    if partition is None or partition["archived_at"] is not None:
        raise HTTPException(status_code=404, detail="Partition not found")
    return partition


@router.get("/partitions/{partition_id}")
def get_partition(
    partition_id: str,
    user: dict = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    partition = _visible(conn, partition_id)
    task = tasks.get_task(conn, partition["task_id"])
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "partition": partition,
        "task": {
            "id": task["id"],
            "name": task["name"],
            "code_key": task["code_key"],
            "code_version": task["code_version"],
            "config": task["config"],
        },
        "items": items.items_with_answers(conn, partition_id, user["id"]),
        "progress": progress.get_progress(conn, user["id"], partition_id),
    }


@router.post("/partitions/{partition_id}/mark-done")
def post_mark_done(
    partition_id: str,
    user: dict = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        status = mark_done(conn, user["id"], partition_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Partition not found") from exc
    return {"list_status": status}


@router.post("/partitions/{partition_id}/reopen")
def post_reopen(
    partition_id: str,
    user: dict = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        status = reopen(conn, user["id"], partition_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Partition not found") from exc
    return {"list_status": status}
