"""chorus migrate, and the file list a partition needs synced."""

from __future__ import annotations

import argparse
import sys

from chorus.config import settings
from chorus.db.connection import connect
from chorus.db.migrate import migrate
from chorus.db.queries import items, partitions, tasks
from chorus.media import load_manifest
from chorus.tasks.registry import get_task_type


def _file_ids(project: str, partition: str) -> list[str]:
    conn = connect(project)
    try:
        if partition == "all":
            rows = [
                row
                for row in partitions.admin_rows(conn)
                if row["archived_at"] is None
            ]
        else:
            row = partitions.get_partition(conn, partition)
            if row is None:
                raise SystemExit(f"Unknown partition {partition}")
            rows = [row]
        found: list[str] = []
        seen: set[str] = set()
        for row in rows:
            task = tasks.get_task(conn, row["task_id"])
            if task is None:
                continue
            task_type = get_task_type(task["code_key"])
            for item in items.list_items(conn, row["id"]):
                for file_id in task_type.required_files(item["locator"]):
                    if file_id not in seen:
                        seen.add(file_id)
                        found.append(file_id)
        return found
    finally:
        conn.close()


def cmd_files(project: str, partition: str) -> int:
    if project not in settings().projects:
        print(f"Unknown project {project}", file=sys.stderr)
        return 1
    manifest = load_manifest(project)
    missing = []
    for file_id in _file_ids(project, partition):
        record = manifest.get("files", {}).get(file_id)
        if not record:
            missing.append(file_id)
            continue
        print(record["path"])
    if missing:
        print("Missing from manifest:", file=sys.stderr)
        for file_id in missing:
            print(f"  {file_id}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chorus")
    sub = parser.add_subparsers(dest="cmd", required=True)

    migrate_parser = sub.add_parser("migrate", help="Apply pending SQL migrations")
    migrate_parser.add_argument("--project", required=True)

    files_parser = sub.add_parser("files", help="Print raw files a partition needs")
    files_parser.add_argument("--project", required=True)
    files_parser.add_argument("--partition", required=True, help="Partition id, or all")

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        applied = migrate(args.project)
        if applied:
            print("Applied " + ", ".join(applied))
        else:
            print("No pending migrations")
        return 0
    if args.cmd == "files":
        return cmd_files(args.project, args.partition)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
