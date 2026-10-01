"""Process settings, read from the environment on every call."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# backend/chorus/config.py -> parents[3] is the folder that holds chorus/, db/, and data/.
_DEFAULT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    root: Path
    secret_key: str
    registration_key: str
    admin_key: str
    port: int
    projects: tuple[str, ...]

    def db_path(self, project: str) -> Path:
        return self.root / "db" / f"{project}.sqlite"

    def data_dir(self, project: str) -> Path:
        return self.root / "data" / project

    def manifest_path(self, project: str) -> Path:
        return self.data_dir(project) / "manifest.json"


def settings() -> Settings:
    projects = tuple(
        part.strip()
        for part in os.environ.get("CHORUS_PROJECTS", "voices").split(",")
        if part.strip()
    )
    return Settings(
        root=Path(os.environ.get("CHORUS_ROOT", str(_DEFAULT_ROOT))).expanduser(),
        secret_key=os.environ.get("CHORUS_SECRET_KEY", "dev-only-change-me"),
        registration_key=os.environ.get("CHORUS_REGISTRATION_KEY", ""),
        admin_key=os.environ.get("CHORUS_ADMIN_KEY", ""),
        port=int(os.environ.get("CHORUS_PORT", "1945")),
        projects=projects,
    )
