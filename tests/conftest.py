"""Isolated Chorus root for each test."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))


@pytest.fixture
def chorus_root(tmp_path, monkeypatch):
    root = tmp_path / "chorus-root"
    (root / "db").mkdir(parents=True)
    (root / "data").mkdir(parents=True)
    monkeypatch.setenv("CHORUS_ROOT", str(root))
    monkeypatch.setenv("CHORUS_SECRET_KEY", "test-secret")
    monkeypatch.setenv("CHORUS_REGISTRATION_KEY", "test-reg-key")
    monkeypatch.setenv("CHORUS_ADMIN_KEY", "test-admin-key")
    monkeypatch.setenv("CHORUS_PROJECTS", "voices")
    monkeypatch.setenv("CHORUS_PORT", "1945")
    return root


@pytest.fixture
def migrated(chorus_root):
    from chorus.db.migrate import migrate

    migrate("voices")
    return chorus_root


@pytest.fixture
def client(migrated):
    from fastapi.testclient import TestClient

    from chorus.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
