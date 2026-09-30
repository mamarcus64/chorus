#!/usr/bin/env python3
"""Three-way row merge of a Chorus SQLite file.

A file copy cannot merge two databases. This compares each row with the last
shared copy and keeps a change that happened on only one side. A primary key
changed on both sides is a conflict.

  python scripts/merge.py base.sqlite local.sqlite remote.sqlite -o merged.sqlite
  python scripts/merge.py base.sqlite local.sqlite remote.sqlite -o merged.sqlite --prefer newer
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def checkpoint(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def load(path: Path) -> tuple[list[str], dict, dict, set]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    schema: list[str] = []
    tables: list[str] = []
    rows = conn.execute(
        """
        SELECT type, name, sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
        ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END, name
        """
    ).fetchall()
    for row in rows:
        schema.append(row["sql"])
        if row["type"] == "table":
            tables.append(row["name"])
    data: dict[str, dict] = {}
    meta: dict[str, dict] = {}
    for table in tables:
        info = conn.execute(f"PRAGMA table_info({quote(table)})").fetchall()
        columns = [row["name"] for row in info]
        pk = [row["name"] for row in sorted(info, key=lambda item: item["pk"]) if row["pk"]]
        if not pk:
            raise SystemExit(f"{table} has no primary key, so rows cannot be merged")
        stored: dict[tuple, dict] = {}
        for record in conn.execute(f"SELECT * FROM {quote(table)}"):
            item = {column: record[column] for column in columns}
            stored[tuple(item[column] for column in pk)] = item
        uniques = []
        for index in conn.execute(f"PRAGMA index_list({quote(table)})"):
            if not index["unique"] or index["origin"] == "pk":
                continue
            parts = [
                row["name"]
                for row in conn.execute(f"PRAGMA index_info({quote(index['name'])})")
            ]
            uniques.append(parts)
        data[table] = stored
        meta[table] = {"columns": columns, "pk": pk, "unique": uniques}
    versions = set(data.get("schema_migrations", {}))
    conn.close()
    return schema, data, meta, versions


def _newer(left: dict | None, right: dict | None) -> dict | None:
    if left is None:
        return right
    if right is None:
        return left
    left_time = left.get("updated_at") or ""
    right_time = right.get("updated_at") or ""
    if left_time == right_time:
        return None
    return left if left_time > right_time else right


def merge_rows(base: dict, local: dict, remote: dict, meta: dict, prefer: str | None):
    conflicts = []
    merged: dict[str, dict] = {}
    for table, info in meta.items():
        base_rows = base.get(table, {})
        local_rows = local.get(table, {})
        remote_rows = remote.get(table, {})
        out: dict[tuple, dict] = {}
        for key in set(base_rows) | set(local_rows) | set(remote_rows):
            before = base_rows.get(key)
            left = local_rows.get(key)
            right = remote_rows.get(key)
            if table == "schema_migrations" and left is not None and right is not None:
                out[key] = left if (left.get("updated_at") or "") >= (right.get("updated_at") or "") else right
                continue
            if left == right:
                if left is not None:
                    out[key] = left
                continue
            if left == before:
                if right is not None:
                    out[key] = right
                continue
            if right == before:
                if left is not None:
                    out[key] = left
                continue
            chosen = _newer(left, right) if prefer == "newer" else None
            conflicts.append(
                {
                    "table": table,
                    "pk": list(key),
                    "local": left,
                    "remote": right,
                    "resolved": chosen is not None,
                }
            )
            if chosen is not None:
                out[key] = chosen
        merged[table] = out
    return merged, conflicts


def unique_collisions(merged: dict, meta: dict) -> list[dict]:
    problems = []
    for table, info in meta.items():
        rows = list(merged[table].values())
        for columns in info["unique"]:
            seen: dict[tuple, dict] = {}
            for row in rows:
                key = tuple(row[column] for column in columns)
                if any(part is None for part in key):
                    continue
                if key in seen:
                    problems.append(
                        {"table": table, "columns": columns, "value": list(key)}
                    )
                else:
                    seen[key] = row
    return problems


def write_db(schema: list[str], merged: dict, meta: dict, dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    conn = sqlite3.connect(dest)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        for statement in schema:
            conn.execute(statement)
        for table, info in meta.items():
            columns = info["columns"]
            column_sql = ", ".join(quote(column) for column in columns)
            placeholders = ", ".join("?" for _ in columns)
            sql = f"INSERT INTO {quote(table)} ({column_sql}) VALUES ({placeholders})"
            for row in merged[table].values():
                conn.execute(sql, [row[column] for column in columns])
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
        bad = conn.execute("PRAGMA foreign_key_check").fetchall()
        if bad:
            raise SystemExit(f"Foreign key check failed: {bad}")
    finally:
        conn.close()


def merge(base: Path, local: Path, remote: Path, output: Path, prefer: str | None, report_path: Path) -> int:
    for path in (base, local, remote):
        if not path.is_file():
            raise SystemExit(f"Missing database {path}")
        checkpoint(path)
    base_schema, base_data, base_meta, base_versions = load(base)
    local_schema, local_data, local_meta, local_versions = load(local)
    _, remote_data, remote_meta, remote_versions = load(remote)
    del base_schema, base_meta
    if local_versions != remote_versions or local_versions != base_versions:
        raise SystemExit(
            "schema_migrations do not match. Apply the same migrations to every copy before merging."
        )
    if set(local_meta) != set(remote_meta):
        raise SystemExit("The copies do not have the same tables.")
    merged, conflicts = merge_rows(base_data, local_data, remote_data, local_meta, prefer)
    collisions = unique_collisions(merged, local_meta)
    unresolved = [item for item in conflicts if not item["resolved"]]
    report = {"conflicts": conflicts, "unique_collisions": collisions}
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    if unresolved or collisions:
        print(
            f"{len(unresolved)} conflict(s), {len(collisions)} unique collision(s). See {report_path}",
            file=sys.stderr,
        )
        return 1
    write_db(local_schema, merged, local_meta, output)
    print(f"Wrote {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Three-way merge of a Chorus SQLite database")
    parser.add_argument("base")
    parser.add_argument("local")
    parser.add_argument("remote")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--prefer", choices=["newer"], default=None)
    parser.add_argument("--report", default=None, help="Defaults to merge_report.json beside the output")
    args = parser.parse_args(argv)
    output = Path(args.output)
    report = Path(args.report) if args.report else output.parent / "merge_report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    return merge(Path(args.base), Path(args.local), Path(args.remote), output, args.prefer, report)


if __name__ == "__main__":
    raise SystemExit(main())
