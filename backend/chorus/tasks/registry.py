"""Code task types, looked up by code_key."""

from __future__ import annotations

from chorus.tasks.base import TaskType
from chorus.tasks.frame_choice.task import FrameChoice

_TYPES: dict[str, TaskType] = {FrameChoice.code_key: FrameChoice()}


def get_task_type(code_key: str) -> TaskType:
    try:
        return _TYPES[code_key]
    except KeyError as exc:
        raise KeyError(f"unknown task type {code_key}") from exc


def registered_keys() -> list[str]:
    return sorted(_TYPES)
