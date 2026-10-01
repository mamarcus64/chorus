"""Assignment and archive. Creating partitions stays on the builder."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from chorus.api.deps import admin_user, get_conn
from chorus.db.queries import annotations, items, partitions, progress, tasks, users

router = APIRouter()


class AssignmentBody(BaseModel):
    mode: str
    user_ids: list[str] = []


class ArchiveBody(BaseModel):
    archived: bool


class MembershipBody(BaseModel):
    partition_ids: list[str] = []


def _choice_labels(config: dict) -> dict[str, str]:
    labels: dict[str, str] = {}
    choices = config.get("choices") if isinstance(config, dict) else None
    if not isinstance(choices, list):
        return labels
    for choice in choices:
        if isinstance(choice, dict) and "value" in choice:
            labels[str(choice["value"])] = str(choice.get("label") or choice["value"])
    return labels


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


@router.get("/admin/summary")
def admin_summary(
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    listed = []
    for row in partitions.summary_rows(conn):
        listed.append(
            {
                "id": row["id"],
                "name": row["name"],
                "task_name": row["task_name"],
                "assignment": row["assignment"],
                "archived_at": row["archived_at"],
                "item_count": int(row["item_count"]),
                "assignee_count": int(row["assignee_count"]),
                "annotator_count": int(row["annotator_count"]),
                "assigned_started": int(row["assigned_started"]),
                "done_count": int(row["done_count"]),
            }
        )
    return {"partitions": listed}


@router.get("/admin/partitions/{partition_id}")
def admin_partition(
    partition_id: str,
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    partition = partitions.get_partition(conn, partition_id)
    if partition is None:
        raise HTTPException(status_code=404, detail="Partition not found")
    task = tasks.get_task(conn, partition["task_id"])
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    labels = _choice_labels(task["config"])
    answers = []
    for row in annotations.choice_counts(conn, partition_id):
        choice = row["choice"]
        key = "" if choice is None else str(choice)
        answers.append(
            {
                "choice": choice,
                "label": labels.get(key, key or "—"),
                "count": row["count"],
            }
        )
    people = []
    for row in partitions.partition_user_rows(conn, partition_id):
        people.append(
            {
                "id": row["id"],
                "username": row["username"],
                "is_admin": bool(row["is_admin"]),
                "answered_count": int(row["answered_count"]),
                "status": row["status"],
                "done_via": row["done_via"],
                "is_assignee": bool(row["is_assignee"]),
            }
        )
    return {
        "id": partition["id"],
        "name": partition["name"],
        "description": partition["description"],
        "task_name": task["name"],
        "assignment": partition["assignment"],
        "archived_at": partition["archived_at"],
        "item_count": items.count_items(conn, partition_id),
        "assignees": partitions.assignee_ids(conn, partition_id),
        "users": people,
        "answers": answers,
    }


@router.get("/admin/users")
def admin_users(
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    listed = []
    for row in users.people_rows(conn):
        listed.append(
            {
                "id": row["id"],
                "username": row["username"],
                "is_admin": bool(row["is_admin"]),
                "selected_count": int(row["selected_count"]),
                "answered_count": int(row["answered_count"]),
                "done_count": int(row["done_count"]),
            }
        )
    return {"users": listed}


@router.get("/admin/users/{user_id}")
def admin_user_detail(
    user_id: str,
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    person = users.get_user(conn, user_id)
    if person is None:
        raise HTTPException(status_code=404, detail="User not found")
    listed = []
    for row in partitions.person_partition_rows(conn, user_id):
        listed.append(
            {
                "id": row["id"],
                "name": row["name"],
                "task_name": row["task_name"],
                "assignment": row["assignment"],
                "archived_at": row["archived_at"],
                "item_count": int(row["item_count"]),
                "is_assignee": bool(row["is_assignee"]),
                "answered_count": int(row["answered_count"]),
                "status": row["status"],
                "done_via": row["done_via"],
            }
        )
    return {
        "user": {
            "id": person["id"],
            "username": person["username"],
            "is_admin": bool(person["is_admin"]),
        },
        "partitions": listed,
    }


@router.put("/admin/users/{user_id}/assignments")
def put_user_assignments(
    user_id: str,
    body: MembershipBody,
    admin: dict = Depends(admin_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    del admin
    if users.get_user(conn, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        partitions.set_user_selected_membership(conn, user_id, body.partition_ids)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="Unknown partition") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Only partitions assigned to selected people can be set here",
        ) from exc
    return {
        "user_id": user_id,
        "partition_ids": [
            row["id"]
            for row in partitions.person_partition_rows(conn, user_id)
            if row["assignment"] == "selected" and row["is_assignee"]
        ],
    }


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
