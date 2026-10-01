"""Admin summary, partition detail, and per-person assignment."""

from chorus.db.connection import connect
from chorus.db.queries import items, partitions, tasks


def _register(client, name):
    response = client.post(
        "/api/p/voices/auth/register",
        json={"username": name, "password": "password1", "registration_key": "test-reg-key"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _login(client, name, admin_key=""):
    response = client.post(
        "/api/p/voices/auth/login",
        json={"username": name, "password": "password1", "admin_key": admin_key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _seed():
    conn = connect("voices")
    try:
        task = tasks.upsert_task(
            conn,
            name="Head present",
            code_key="frame_choice",
            code_version=1,
            config={
                "prompt": "Is a human head inside the box?",
                "choices": [
                    {"value": "yes", "label": "Yes", "key": "1"},
                    {"value": "no", "label": "No", "key": "2"},
                ],
                "overlays": ["bbox"],
                "instructions": "Look at the box.",
            },
        )
        pilot = partitions.upsert_partition(
            conn, task_id=task["id"], name="pilot", description=None, config={}
        )
        other = partitions.upsert_partition(
            conn, task_id=task["id"], name="later", description=None, config={}
        )
        item = items.upsert_item(
            conn,
            partition_id=pilot["id"],
            ordinal=0,
            kind="frame",
            locator={"source": "usc", "video_id": "10.1", "frame": 4, "time_s": 0.1, "still": "still:usc:10.1:4"},
            features={},
        )
        return pilot, other, item
    finally:
        conn.close()


def test_summary_detail_and_person_assignment(client):
    ada = _register(client, "ada")
    client.post("/api/p/voices/auth/logout")
    denied = client.get("/api/p/voices/admin/summary")
    assert denied.status_code == 401

    _login(client, "ada", "test-admin-key")
    pilot, later, item = _seed()
    saved = client.put(
        f"/api/p/voices/items/{item['id']}/annotation",
        json={"value": {"choice": "yes"}, "elapsed_ms": 12},
    )
    assert saved.status_code == 200

    summary = client.get("/api/p/voices/admin/summary")
    assert summary.status_code == 200
    rows = {row["name"]: row for row in summary.json()["partitions"]}
    assert rows["pilot"]["annotator_count"] == 1
    assert rows["pilot"]["done_count"] == 1
    assert rows["pilot"]["assignment"] == "everyone"
    assert rows["pilot"]["assignee_count"] == 0

    detail = client.get(f"/api/p/voices/admin/partitions/{pilot['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["answers"] == [{"choice": "yes", "label": "Yes", "count": 1}]
    ada_row = next(person for person in body["users"] if person["id"] == ada["id"])
    assert ada_row["answered_count"] == 1
    assert ada_row["status"] == "done"
    assert ada_row["done_via"] == "answers"
    assert "password_hash" not in body["users"][0]

    narrowed = client.put(
        f"/api/p/voices/admin/partitions/{pilot['id']}/assignment",
        json={"mode": "selected", "user_ids": [ada["id"]]},
    )
    assert narrowed.status_code == 200
    client.post("/api/p/voices/auth/logout")
    bea = _register(client, "bea")
    client.post("/api/p/voices/auth/logout")
    _login(client, "ada")

    blocked = client.put(
        f"/api/p/voices/admin/users/{bea['id']}/assignments",
        json={"partition_ids": [later["id"]]},
    )
    assert blocked.status_code == 400

    added = client.put(
        f"/api/p/voices/admin/users/{bea['id']}/assignments",
        json={"partition_ids": [pilot["id"]]},
    )
    assert added.status_code == 200
    assert added.json()["partition_ids"] == [pilot["id"]]

    people = client.get("/api/p/voices/admin/users").json()["users"]
    bea_row = next(person for person in people if person["id"] == bea["id"])
    assert bea_row["selected_count"] == 1
    assert "password_hash" not in bea_row

    client.post("/api/p/voices/auth/logout")
    _login(client, "bea")
    home = client.get("/api/p/voices/home").json()
    assert [row["name"] for row in home["todo"]] == ["later", "pilot"]
    client.post("/api/p/voices/auth/logout")
    _login(client, "ada")

    cleared = client.put(
        f"/api/p/voices/admin/users/{bea['id']}/assignments",
        json={"partition_ids": []},
    )
    assert cleared.json()["partition_ids"] == []
    client.post("/api/p/voices/auth/logout")
    _login(client, "bea")
    home = client.get("/api/p/voices/home").json()
    assert [row["name"] for row in home["not_assigned"]] == ["pilot"]
    assert [row["name"] for row in home["todo"]] == ["later"]

    client.post("/api/p/voices/auth/logout")
    _login(client, "ada")
    person = client.get(f"/api/p/voices/admin/users/{ada['id']}")
    assert person.status_code == 200
    pilot_row = next(row for row in person.json()["partitions"] if row["id"] == pilot["id"])
    assert pilot_row["is_assignee"] is True
    assert person.json()["user"]["is_admin"] is True
