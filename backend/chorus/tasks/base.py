"""The contract every task type implements. Task types are code, shared across projects."""

from __future__ import annotations

from typing import Protocol


class TaskError(ValueError):
    """The config, the item, or the answer does not match this task type."""


class TaskType(Protocol):
    code_key: str
    code_version: int
    item_kinds: set[str]

    def validate_config(self, config: dict) -> dict: ...

    def validate_item(self, kind: str, locator: dict, features: dict) -> None: ...

    def validate_value(self, config: dict, value: dict) -> dict: ...

    def required_files(self, locator: dict) -> list[str]: ...
