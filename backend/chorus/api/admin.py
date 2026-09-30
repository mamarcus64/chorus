"""Assignment and archive. Creating partitions stays on the builder."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from chorus.api.deps import admin_user, get_conn
from chorus.db.queries import annotations, partitions, progress, users

router = APIRouter()


class AssignmentBody(BaseModel):
    mode: str
    user_ids: list[str] = []


class ArchiveBody(BaseModel):
    archived: bool


@router.get("/admin/partitions")
def admin_partitions(
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    people = users.list_users(conn)
    public_people = [
        {"id": person["id"], "username": person["username"], "is_admin": bool(person["is_admin"])}
        for person in people
    ]
    listed = []
    for row in partitions.admin_rows(conn):
        counts = annotations.counts_by_user(conn, row["id"])
        states = {item["user_id"]: item for item in progress.progress_for_partition(conn, row["id"])}
        user_rows = []
        for person in people:
            state = states.get(person["id"])
            user_rows.append(
                {
                    "id": person["id"],
                    "username": person["username"],
                    "answered_count": counts.get(person["id"], 0),
                    "status": None if state is None else state["status"],
                    "done_via": None if state is None else state["done_via"],
                }
            )
        listed.append(
            {
                "id": row["id"],
                "name": row["name"],
                "task_name": row["task_name"],
                "code_key": row["code_key"],
                "assignment": row["assignment"],
                "archived_at": row["archived_at"],
                "item_count": row["item_count"],
                "assignees": partitions.assignee_ids(conn, row["id"]),
                "users": user_rows,
            }
        )
    return {"partitions": listed, "users": public_people}


@router.put("/admin/partitions/{partition_id}/assignment")
def put_assignment(
    partition_id: str,
    body: AssignmentBody,
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    if body.mode not in ("everyone", "selected"):
        raise HTTPException(status_code=400, detail="mode must be everyone or selected")
    partition = partitions.get_partition(conn, partition_id)
    if partition is None:
        raise HTTPException(status_code=404, detail="Partition not found")
    known = {person["id"] for person in users.list_users(conn)}
    unknown = [user_id for user_id in body.user_ids if user_id not in known]
    if unknown:
        raise HTTPException(status_code=400, detail="Unknown user id")
    partitions.set_assignment_mode(conn, partition_id, body.mode)
    partitions.replace_assignees(conn, partition_id, body.user_ids if body.mode == "selected" else [])
    return {
        "id": partition_id,
        "assignment": body.mode,
        "assignees": partitions.assignee_ids(conn, partition_id),
    }


@router.put("/admin/partitions/{partition_id}/archive")
def put_archive(
    partition_id: str,
    body: ArchiveBody,
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    try:
        partition = partitions.set_archived(conn, partition_id, body.archived)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Partition not found") from exc
    return {"id": partition["id"], "archived_at": partition["archived_at"]}
