"""Home-page lists: everyone, selected, later users, done, reopen, edits."""

from chorus.db.connection import connect
from chorus.db.queries import items, partitions, tasks, users
from chorus.services import lists


def _seed(conn, n=2):
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
        conn,
        task_id=task["id"],
        name="pilot",
        description=None,
        config={"seed": 1, "n": n, "min_score": 0.9, "sources": ["usc"]},
    )
    made = []
    for index in range(n):
        locator = {
            "source": "usc",
            "video_id": "10.1",
            "frame": index,
            "time_s": float(index),
            "still": f"still:usc:10.1:{index}",
        }
        made.append(
            items.upsert_item(
                conn,
                partition_id=partition["id"],
                ordinal=index,
                kind="frame",
                locator=locator,
                features={"bbox": [1, 2, 3, 4], "face_score": 0.95, "image_size": [320, 240]},
            )
        )
    return partition, made


def _names(home, bucket):
    return [row["name"] for row in home[bucket]]


def test_default_is_everyone_and_a_later_user_is_included(migrated):
    conn = connect("voices")
    try:
        partition, _ = _seed(conn, 1)
        ada = users.create_user(conn, "ada", "hash")
        home = lists.home(conn, ada["id"])
        assert _names(home, "todo") == ["pilot"]
        assert home["not_assigned"] == []
        assert home["done"] == []

        partitions.set_assignment_mode(conn, partition["id"], "selected")
        partitions.replace_assignees(conn, partition["id"], [ada["id"]])
        bea = users.create_user(conn, "bea", "hash")
        assert _names(lists.home(conn, ada["id"]), "todo") == ["pilot"]
        assert _names(lists.home(conn, bea["id"]), "not_assigned") == ["pilot"]
        assert lists.home(conn, bea["id"])["todo"] == []
    finally:
        conn.close()


def test_automatic_done_mark_done_reopen_and_edit(migrated):
    conn = connect("voices")
    try:
        partition, made = _seed(conn, 2)
        ada = users.create_user(conn, "ada", "hash")
        first = lists.save_annotation(
            conn, user_id=ada["id"], item_id=made[0]["id"], value={"choice": "yes"}, elapsed_ms=10
        )
        assert first["list_status"] == "todo"
        lists.mark_done(conn, ada["id"], partition["id"])
        assert _names(lists.home(conn, ada["id"]), "done") == ["pilot"]
        assert lists.home(conn, ada["id"])["done"][0]["done_via"] == "marked"

        lists.reopen(conn, ada["id"], partition["id"])
        # Answers are still there, but a page load does not close the partition again.
        home = lists.home(conn, ada["id"])
        assert _names(home, "todo") == ["pilot"]
        assert home["todo"][0]["answered_count"] == 1

        second = lists.save_annotation(
            conn, user_id=ada["id"], item_id=made[1]["id"], value={"choice": "no"}, elapsed_ms=12
        )
        assert second["list_status"] == "done"
        assert lists.home(conn, ada["id"])["done"][0]["done_via"] == "answers"

        lists.reopen(conn, ada["id"], partition["id"])
        edited = lists.save_annotation(
            conn, user_id=ada["id"], item_id=made[0]["id"], value={"choice": "unsure"}, elapsed_ms=4
        )
        assert edited["annotation"]["value"] == {"choice": "unsure"}
        assert edited["list_status"] == "done"
        again = lists.save_annotation(
            conn, user_id=ada["id"], item_id=made[0]["id"], value={"choice": "yes"}, elapsed_ms=5
        )
        assert again["annotation"]["id"] == edited["annotation"]["id"]
        assert again["annotation"]["value"] == {"choice": "yes"}
    finally:
        conn.close()
