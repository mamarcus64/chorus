import threading

from chorus.db.connection import connect
from chorus.db.migrate import migrate


def test_connection_can_be_used_from_another_thread(chorus_root):
    migrate("voices")
    conn = connect("voices")
    errors: list[BaseException] = []

    def work() -> None:
        try:
            conn.execute("SELECT 1").fetchone()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    conn.close()
    assert errors == []


def test_migrations_apply_once(chorus_root):
    first = migrate("voices")
    assert first == ["0001_init"]
    second = migrate("voices")
    assert second == []
    conn = connect("voices")
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        versions = [row["version"] for row in conn.execute("SELECT version FROM schema_migrations")]
    finally:
        conn.close()
    assert versions == ["0001_init"]
    for name in (
        "users",
        "tasks",
        "partitions",
        "items",
        "partition_assignees",
        "partition_progress",
        "annotations",
    ):
        assert name in tables
    assert chorus_root.joinpath("db", "voices.sqlite").is_file()


def test_sql_stays_in_the_query_layer():
    root = REPO = __import__("pathlib").Path(__file__).resolve().parents[1]
    package = root / "backend" / "chorus"
    allowed = {"queries", "migrate.py", "connection.py"}
    offenders = []
    for path in package.rglob("*.py"):
        if any(part in allowed for part in path.parts) or path.name in allowed:
            continue
        text = path.read_text()
        for token in ("INSERT ", "SELECT ", "UPDATE ", "DELETE "):
            if token in text:
                offenders.append(f"{path.relative_to(package)} contains {token.strip()}")
    assert offenders == []
