"""Deterministic ids so a rebuilt partition keeps the same rows."""

from __future__ import annotations

import json
import uuid

NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://chorus.annotation/ns")


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _uuid5(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def task_id(name: str) -> str:
    return _uuid5("task:" + name)


def partition_id(task: str, name: str) -> str:
    return _uuid5(f"partition:{task}:{name}")


def item_id(partition: str, locator: dict) -> str:
    return _uuid5("item:" + partition + ":" + canonical_json(locator))


def annotation_id(user: str, item: str) -> str:
    return _uuid5(f"annotation:{user}:{item}")
