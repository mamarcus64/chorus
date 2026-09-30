"""The HTTP surface: lists, answers, admin assignment, and media."""

from chorus.db.connection import connect, utcnow
from chorus.db.queries import items, partitions, tasks
from chorus.media import upsert_manifest_file


def _register(client, name):
    response = client.post(
        "/api/p/voices/auth/register",
        json={"username": name, "password": "password1", "registration_key": "test-reg-key"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _seed_one():
    conn = connect("voices")
    try:
        task = tasks.upsert_task(
            conn,
            name="Head present (face_score > 0.9)",
            code_key="frame_choice",
            code_version=1,
            config={
                "prompt": "Is a human head inside the box?",
                "choices": [
                    {"value": "yes", "label": "Yes", "key": "1"},
                    {"value": "no", "label": "No", "key": "2"},
                    {"value": "unsure", "label": "Unsure", "key": "3"},
                ],
                "overlays": ["bbox"],
                "instructions": "Look at the box.",
            },
        )
        partition = partitions.upsert_partition(
            conn, task_id=task["id"], name="pilot", description=None, config={}
        )
        item = items.upsert_item(
            conn,
            partition_id=partition["id"],
            ordinal=0,
            kind="frame",
            locator={"source": "usc", "video_id": "10.1", "frame": 4, "time_s": 0.1, "still": "still:usc:10.1:4"},
            features={"bbox": [1, 2, 30, 40], "face_score": 0.99, "image_size": [320, 240]},
        )
        return partition, item
    finally:
        conn.close()


def test_answer_completes_the_partition_and_admin_can_narrow_it(client, migrated):
    ada = _register(client, "ada")
    partition, item = _seed_one()
    home = client.get("/api/p/voices/home")
    assert home.status_code == 200
    assert [row["name"] for row in home.json()["todo"]] == ["pilot"]

    denied = client.get("/api/p/voices/admin/partitions")
    assert denied.status_code == 403

    bad = client.put(
        f"/api/p/voices/items/{item['id']}/annotation",
        json={"value": {"choice": "maybe"}, "elapsed_ms": 5},
    )
    assert bad.status_code == 400

    saved = client.put(
        f"/api/p/voices/items/{item['id']}/annotation",
        json={"value": {"choice": "yes"}, "elapsed_ms": 15},
    )
    assert saved.status_code == 200
    assert saved.json()["list_status"] == "done"

    detail = client.get(f"/api/p/voices/partitions/{partition['id']}")
    assert detail.json()["items"][0]["answer"] == {"choice": "yes"}

    reopened = client.post(f"/api/p/voices/partitions/{partition['id']}/reopen")
    assert reopened.json()["list_status"] == "todo"
    still = client.get("/api/p/voices/home").json()
    assert still["todo"][0]["name"] == "pilot"
    assert still["todo"][0]["answered_count"] == 1

    conn = connect("voices")
    try:
        conn.execute(
            "UPDATE users SET is_admin = 1, updated_at = ? WHERE id = ?",
            (utcnow(), ada["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    client.post("/api/p/voices/auth/logout")
    client.post(
        "/api/p/voices/auth/login",
        json={"username": "ada", "password": "password1"},
    )
    client.post("/api/p/voices/auth/logout")
    _register(client, "bea")
    client.post("/api/p/voices/auth/logout")
    client.post(
        "/api/p/voices/auth/login",
        json={"username": "ada", "password": "password1"},
    )

    admin = client.get("/api/p/voices/admin/partitions")
    assert admin.status_code == 200
    narrowed = client.put(
        f"/api/p/voices/admin/partitions/{partition['id']}/assignment",
        json={"mode": "selected", "user_ids": [ada["id"]]},
    )
    assert narrowed.status_code == 200
    client.post("/api/p/voices/auth/logout")
    client.post(
        "/api/p/voices/auth/login",
        json={"username": "bea", "password": "password1"},
    )
    bea_home = client.get("/api/p/voices/home").json()
    assert [row["name"] for row in bea_home["not_assigned"]] == ["pilot"]
    assert bea_home["todo"] == []

    image = migrated / "data" / "voices" / "stills" / "frame.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\xff\xd8\xff\xd9")
    upsert_manifest_file(
        "voices",
        "still:usc:10.1:4",
        {"path": "stills/frame.jpg", "kind": "image", "bytes": image.stat().st_size, "source": {}},
    )
    media = client.get("/api/p/voices/media/still%3Ausc%3A10.1%3A4")
    assert media.status_code == 200
    assert media.content.startswith(b"\xff\xd8")
    client.post("/api/p/voices/auth/logout")
    assert client.get("/api/p/voices/media/still%3Ausc%3A10.1%3A4").status_code == 401
