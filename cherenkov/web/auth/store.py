"""SQLite-backed user store. Uses stdlib only (no bcrypt/passlib dependency)."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
from pathlib import Path

from cherenkov.web.auth.models import Role, User, UserInDB

_DEFAULT_DB = Path.home() / ".cherenkov" / "auth.db"
_PBKDF2_ITERS = 260_000


def _db_path() -> Path:
    env = os.getenv("CHERENKOV_AUTH_DB")
    return Path(env) if env else _DEFAULT_DB


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERS)
    return f"pbkdf2:sha256:{_PBKDF2_ITERS}:{salt}:{dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, algo, iters, salt, dk_hex = stored.split(":")
        dk = hashlib.pbkdf2_hmac(algo, password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


class UserStore:
    def __init__(self, db_path: Path | None = None):
        self._path = db_path or _db_path()
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username        TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    role            TEXT NOT NULL DEFAULT 'viewer',
                    disabled        INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    def count(self) -> int:
        with self._lock, self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def create(self, username: str, password: str, role: Role = Role.viewer) -> User:
        hashed = _hash_password(password)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                (username, hashed, role.value),
            )
            conn.commit()
        return User(username=username, role=role)

    def get(self, username: str) -> UserInDB | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not row:
            return None
        return UserInDB(
            username=row["username"],
            hashed_password=row["hashed_password"],
            role=Role(row["role"]),
            disabled=bool(row["disabled"]),
        )

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.get(username)
        if not user or user.disabled:
            return None
        if not _verify_password(password, user.hashed_password):
            return None
        return User(username=user.username, role=user.role)

    def list_users(self) -> list[User]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT username, role, disabled FROM users").fetchall()
        return [User(username=r["username"], role=Role(r["role"]), disabled=bool(r["disabled"])) for r in rows]

    def set_disabled(self, username: str, disabled: bool) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET disabled = ? WHERE username = ?",
                (int(disabled), username),
            )
            conn.commit()
        return cur.rowcount > 0


_store: UserStore | None = None
_store_lock = threading.Lock()


def get_user_store() -> UserStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = UserStore()
    return _store
