"""Row merge: one-sided edits apply, both-sided edits conflict."""

import json
import shutil
import sqlite3
from pathlib import Path

from chorus.db.connection import connect
from chorus.db.queries import annotations, items, partitions, tasks, users

MERGE = Path(__file__).resolve().parents[1] / "scripts" / "merge.py"


def _snapshot(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    source = sqlite3.connect(src)
    source.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    backup = sqlite3.connect(dest)
    source.backup(backup)
    backup.close()
    source.close()


def _seed(conn):
    user = users.create_user(conn, "ada", "hash")
    task = tasks.upsert_task(
        conn,
        name="Head present (face_score > 0.9)",
        code_key="frame_choice",
        code_version=1,
        config={"prompt": "Is a human head inside the box?", "choices": [{"value": "yes", "label": "Yes", "key": "1"}], "overlays": [], "instructions": ""},
    )
    partition = partitions.upsert_partition(
        conn, task_id=task["id"], name="pilot", description=None, config={}
    )
    item = items.upsert_item(
        conn,
        partition_id=partition["id"],
        ordinal=0,
        kind="frame",
        locator={"source": "usc", "video_id": "10.1", "frame": 1, "time_s": 0.0, "still": "s"},
        features={},
    )
    annotation = annotations.upsert_annotation(
        conn, user_id=user["id"], item_id=item["id"], value={"choice": "yes"}, elapsed_ms=1
    )
    return user, annotation


def _run(tmp: Path, *args: str) -> int:
    import runpy

    argv = ["merge.py", *args]
    import sys

    old = sys.argv
    sys.argv = argv
    try:
        runpy.run_path(str(MERGE), run_name="__main__")
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    finally:
        sys.argv = old


def test_one_sided_insert_update_and_delete(migrated, tmp_path):
    db = migrated / "db" / "voices.sqlite"
    conn = connect("voices")
    try:
        user, annotation = _seed(conn)
    finally:
        conn.close()
    base = tmp_path / "base.sqlite"
    local = tmp_path / "local.sqlite"
    remote = tmp_path / "remote.sqlite"
    _snapshot(db, base)
    _snapshot(db, local)
    _snapshot(db, remote)

    local_conn = sqlite3.connect(local)
    local_conn.execute("DELETE FROM annotations WHERE id = ?", (annotation["id"],))
    local_conn.execute(
        "INSERT INTO users (id, username, password_hash, is_admin, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("user-bea", "bea", "hash", 0, "2026-01-01T00:00:00.000Z", "2026-01-01T00:00:00.000Z"),
    )
    local_conn.commit()
    local_conn.close()

    remote_conn = sqlite3.connect(remote)
    remote_conn.execute(
        "UPDATE users SET is_admin = 1, updated_at = ? WHERE id = ?",
        ("2026-02-01T00:00:00.000Z", user["id"]),
    )
    remote_conn.commit()
    remote_conn.close()

    output = tmp_path / "merged.sqlite"
    code = _run(tmp_path, str(base), str(local), str(remote), "-o", str(output), "--report", str(tmp_path / "report.json"))
    assert code == 0, (tmp_path / "report.json").read_text()
    check = sqlite3.connect(output)
    check.row_factory = sqlite3.Row
    names = {row["username"] for row in check.execute("SELECT username FROM users")}
    admin = check.execute("SELECT is_admin FROM users WHERE id = ?", (user["id"],)).fetchone()["is_admin"]
    labels = check.execute("SELECT COUNT(*) AS n FROM annotations").fetchone()["n"]
    check.close()
    assert names == {"ada", "bea"}
    assert admin == 1
    assert labels == 0


def test_conflict_stops_unless_prefer_newer(migrated, tmp_path):
    db = migrated / "db" / "voices.sqlite"
    conn = connect("voices")
    try:
        _, annotation = _seed(conn)
    finally:
        conn.close()
    base = tmp_path / "base.sqlite"
    local = tmp_path / "local.sqlite"
    remote = tmp_path / "remote.sqlite"
    _snapshot(db, base)
    _snapshot(db, local)
    _snapshot(db, remote)
    for path, stamp, choice in (
        (local, "2026-03-01T00:00:00.000Z", "no"),
        (remote, "2026-04-01T00:00:00.000Z", "unsure"),
    ):
        handle = sqlite3.connect(path)
        handle.execute(
            "UPDATE annotations SET value = ?, updated_at = ? WHERE id = ?",
            (json.dumps({"choice": choice}), stamp, annotation["id"]),
        )
        handle.commit()
        handle.close()

    blocked = tmp_path / "blocked.sqlite"
    code = _run(tmp_path, str(base), str(local), str(remote), "-o", str(blocked), "--report", str(tmp_path / "blocked.json"))
    assert code == 1
    assert not blocked.exists()
    report = json.loads((tmp_path / "blocked.json").read_text())
    assert report["conflicts"]

    output = tmp_path / "merged.sqlite"
    code = _run(
        tmp_path,
        str(base),
        str(local),
        str(remote),
        "-o",
        str(output),
        "--prefer",
        "newer",
        "--report",
        str(tmp_path / "newer.json"),
    )
    assert code == 0
    handle = sqlite3.connect(output)
    value = handle.execute("SELECT value FROM annotations").fetchone()[0]
    handle.close()
    assert json.loads(value)["choice"] == "unsure"


def test_unique_username_collision_is_reported(migrated, tmp_path):
    db = migrated / "db" / "voices.sqlite"
    base = tmp_path / "base.sqlite"
    local = tmp_path / "local.sqlite"
    remote = tmp_path / "remote.sqlite"
    _snapshot(db, base)
    _snapshot(db, local)
    _snapshot(db, remote)
    for path, user_id in ((local, "local-ada"), (remote, "remote-ada")):
        handle = sqlite3.connect(path)
        handle.execute(
            "INSERT INTO users (id, username, password_hash, is_admin, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (user_id, "ada", "hash", 0, "2026-01-01T00:00:00.000Z", "2026-01-01T00:00:00.000Z"),
        )
        handle.commit()
        handle.close()
    output = tmp_path / "merged.sqlite"
    code = _run(tmp_path, str(base), str(local), str(remote), "-o", str(output), "--report", str(tmp_path / "unique.json"))
    assert code == 1
    report = json.loads((tmp_path / "unique.json").read_text())
    assert report["unique_collisions"]
    assert not output.exists()
