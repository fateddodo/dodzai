"""User profile persistence using SQLite."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from ..models import WorkspaceSettings
from ..utils.paths import app_database_path


class LocalProfileStore:
    """Persist user credentials and settings on disk."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else app_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.row_factory = sqlite3.Row
        self._initialise()

    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._connection:
            self._connection.close()

    # ------------------------------------------------------------------
    def _initialise(self) -> None:
        with self._connection as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash BLOB NOT NULL,
                    salt BLOB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    username TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (username, key),
                    FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    username TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    PRIMARY KEY (username, provider),
                    FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
                )
                """
            )

    # ------------------------------------------------------------------
    def create_user(self, username: str, password: str) -> bool:
        if self._user_exists(username):
            return False
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)
        with self._connection as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, password_hash, salt),
            )
        return True

    def authenticate(self, username: str, password: str) -> bool:
        row = self._connection.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            return False
        expected = row["password_hash"]
        salt = row["salt"]
        attempt = self._hash_password(password, salt)
        return secrets.compare_digest(expected, attempt)

    def set_setting(self, username: str, key: str, value: str) -> None:
        with self._connection as conn:
            conn.execute(
                "INSERT INTO settings (username, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(username, key) DO UPDATE SET value=excluded.value",
                (username, key, value),
            )

    def get_setting(self, username: str, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._connection.execute(
            "SELECT value FROM settings WHERE username = ? AND key = ?", (username, key)
        ).fetchone()
        return row["value"] if row else default

    def set_api_key(self, username: str, provider: str, key: str) -> None:
        with self._connection as conn:
            conn.execute(
                "INSERT INTO api_keys (username, provider, api_key) VALUES (?, ?, ?) "
                "ON CONFLICT(username, provider) DO UPDATE SET api_key=excluded.api_key",
                (username, provider, key),
            )

    def get_api_key(self, username: str, provider: str) -> Optional[str]:
        row = self._connection.execute(
            "SELECT api_key FROM api_keys WHERE username = ? AND provider = ?",
            (username, provider),
        ).fetchone()
        return row["api_key"] if row else None

    def get_settings(self, username: str) -> WorkspaceSettings:
        mode = self.get_setting(username, "mode", "online") or "online"
        default_provider = self.get_setting(username, "default_provider")
        default_model = self.get_setting(username, "default_model")
        provider_keys = {
            row["provider"]: row["api_key"]
            for row in self._connection.execute("SELECT provider, api_key FROM api_keys WHERE username = ?", (username,))
        }
        return WorkspaceSettings(
            username=username,
            mode=mode,
            provider_keys=provider_keys,
            default_provider=default_provider,
            default_model=default_model,
        )

    def list_users(self) -> Iterable[str]:
        for row in self._connection.execute("SELECT username FROM users ORDER BY username"):
            yield row["username"]

    # ------------------------------------------------------------------
    def _user_exists(self, username: str) -> bool:
        row = self._connection.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        return bool(row)

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)

    # Context manager ---------------------------------------------------
    def __enter__(self) -> "LocalProfileStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - cleanup
        try:
            self.close()
        except Exception:
            pass
