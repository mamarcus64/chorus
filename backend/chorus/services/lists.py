"""Which list a partition is on, and when a save marks it done."""

from __future__ import annotations

import sqlite3

from chorus.db.queries import annotations, items, partitions, progress
from chorus.tasks.registry import get_task_type


def classify(row: dict) -> str:
    """One of todo, not_assigned, done. Done wins, including on an unassigned partition."""
    if row["progress_status"] == "done":
        return "done"
    if row["assignment"] == "everyone" or row["is_assignee"]:
        return "todo"
    return "not_assigned"


def _entry(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "task_id": row["task_id"],
        "task_name": row["task_name"],
        "code_key": row["code_key"],
        "assignment": row["assignment"],
        "item_count": row["item_count"],
        "answered_count": row["answered_count"],
        "status": classify(row),
        "done_via": row["done_via"],
    }


def home(conn: sqlite3.Connection, user_id: str) -> dict:
    buckets: dict[str, list[dict]] = {"todo": [], "not_assigned": [], "done": []}
    for row in partitions.home_rows(conn, user_id):
        buckets[classify(row)].append(_entry(row))
    return buckets


def list_status(conn: sqlite3.Connection, user_id: str, partition_id: str) -> str | None:
    rows = partitions.home_rows(conn, user_id, partition_id)
    if not rows:
        return None
    return classify(rows[0])


def save_annotation(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    item_id: str,
    value: dict,
    elapsed_ms: int | None,
) -> dict:
    item = items.get_item(conn, item_id)
    if item is None:
        raise KeyError(item_id)
    from chorus.db.queries import tasks as task_rows

    partition = partitions.get_partition(conn, item["partition_id"])
    if partition is None or partition["archived_at"] is not None:
        raise KeyError(item_id)
    task = task_rows.get_task(conn, partition["task_id"])
    if task is None or task["archived_at"] is not None:
        raise KeyError(item_id)
    task_type = get_task_type(task["code_key"])
    clean = task_type.validate_value(task["config"], value)
    annotation = annotations.upsert_annotation(
        conn,
        user_id=user_id,
        item_id=item_id,
        value=clean,
        elapsed_ms=elapsed_ms,
    )
    total = items.count_items(conn, partition["id"])
    answered = annotations.count_for_user_partition(conn, user_id, partition["id"])
    current = progress.get_progress(conn, user_id, partition["id"])
    if total > 0 and answered >= total and (current is None or current["status"] != "done"):
        progress.set_progress(conn, user_id, partition["id"], "done", "answers")
    return {
        "annotation": annotation,
        "list_status": list_status(conn, user_id, partition["id"]),
        "partition_id": partition["id"],
    }


def mark_done(conn: sqlite3.Connection, user_id: str, partition_id: str) -> str:
    partition = partitions.get_partition(conn, partition_id)
    if partition is None or partition["archived_at"] is not None:
        raise KeyError(partition_id)
    progress.set_progress(conn, user_id, partition_id, "done", "marked")
    status = list_status(conn, user_id, partition_id)
    assert status is not None
    return status


def reopen(conn: sqlite3.Connection, user_id: str, partition_id: str) -> str:
    partition = partitions.get_partition(conn, partition_id)
    if partition is None or partition["archived_at"] is not None:
        raise KeyError(partition_id)
    progress.set_progress(conn, user_id, partition_id, "todo", None)
    status = list_status(conn, user_id, partition_id)
    assert status is not None
    return status
