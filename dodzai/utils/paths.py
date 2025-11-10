"""Filesystem path helpers."""
from __future__ import annotations

from pathlib import Path

from ..models import ensure_workspace_dir


def app_root() -> Path:
    return ensure_workspace_dir()


def app_media_dir() -> Path:
    return app_root() / "media"


def app_database_path() -> Path:
    return app_root() / "workspace.sqlite3"


def app_history_path() -> Path:
    return app_root() / "conversations.json"
