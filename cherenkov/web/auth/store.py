"""SQLite-backed user store. Uses stdlib only (no bcrypt/passlib dependency)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from cherenkov.web.auth.models import Role, User, UserInDB

_log = logging.getLogger(__name__)

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
    except (ValueError, TypeError):
        # Malformed or legacy hash record — never a valid credential.
        _log.error("stored password hash is malformed; rejecting login", exc_info=True)
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


class UserStore:
    """SQLite-backed user storage manager handling user credentials, roles, and status."""

    def __init__(self, db_path: Path | None = None):
        """Initialize UserStore instance with optional custom database path.

        Args:
            db_path: Optional Path object to SQLite database file.
        """
        if db_path is None:
            db_path = _db_path()
        # Support in‑memory SQLite database used in tests
        if isinstance(db_path, str) and db_path == ":memory:":
            self._path = db_path  # keep as string for sqlite3 handling
        else:
            # Resolve to a Path instance for file‑based DBs
            self._path = Path(db_path) if isinstance(db_path, (str, Path)) else db_path
        self._lock = threading.Lock()
        self._conn = None
        self._init_db()

    @contextmanager
    def _connect(self):
        if str(self._path) == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(self._path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
            yield self._conn
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username        TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    role            TEXT NOT NULL DEFAULT 'viewer',
                    disabled        INTEGER NOT NULL DEFAULT 0,
                    organization_id TEXT NOT NULL DEFAULT 'default'
                )
            """)
            try:
                conn.execute("ALTER TABLE users ADD COLUMN organization_id TEXT NOT NULL DEFAULT 'default'")
            except sqlite3.OperationalError:
                pass
            conn.commit()
            conn.commit()

    def count(self) -> int:
        """Count total registered users.

        Returns:
            Total count integer of users in database.
        """
        with self._lock, self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def create(
        self,
        username: str,
        password: str,
        role: Role | str = Role.viewer,
        organization_id: str = "default",
    ) -> User:
        """Create a new user record.

        Args:
            username: Unique username string.
            password: Raw plaintext password string.
            role: Target Role enum member or string name.
            organization_id: Target organization ID string.

        Returns:
            Created User domain object.
        """
        # Normalize role to Role enum
        if isinstance(role, str):
            role = Role(role)
        hashed = _hash_password(password)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO users (username, hashed_password, role, organization_id) VALUES (?, ?, ?, ?)",
                (username, hashed, role.value, organization_id),
            )
            conn.commit()
        return User(username=username, role=role, organization_id=organization_id)

    def get(self, username: str) -> UserInDB | None:
        """Retrieve user record including password hash.

        Args:
            username: Target username string.

        Returns:
            UserInDB instance if found, or None.
        """
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
            organization_id=row["organization_id"],
        )

    def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate user credentials against stored hash.

        Args:
            username: Target username string.
            password: Input password string to verify.

        Returns:
            User object if credentials valid and user enabled, or None.
        """
        user = self.get(username)
        if not user or user.disabled:
            return None
        if not _verify_password(password, user.hashed_password):
            return None
        return User(username=user.username, role=user.role, organization_id=user.organization_id)

    def list_users(self) -> list[User]:
        """List all users without password hashes.

        Returns:
            List of User objects.
        """
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT username, role, disabled, organization_id FROM users").fetchall()
        return [User(username=r["username"], role=Role(r["role"]), disabled=bool(r["disabled"]), organization_id=r["organization_id"]) for r in rows]

    def set_disabled(self, username: str, disabled: bool) -> bool:
        """Set user disabled flag.

        Args:
            username: Target username string.
            disabled: Boolean indicating disabled state.

        Returns:
            True if user record updated, False if user not found.
        """
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET disabled = ? WHERE username = ?",
                (int(disabled), username),
            )
            conn.commit()
        return cur.rowcount > 0


    def update_user(self, username: str, role: Role | None = None, organization_id: str | None = None) -> bool:
        """Update user's role and/or organization_id.

        Args:
            username: Target username.
            role: New Role to set (optional).
            organization_id: New organization ID to set (optional).

        Returns:
            True if user was found and updated, False otherwise.
        """
        if role is None and organization_id is None:
            return False
        with self._lock, self._connect() as conn:
            fields = []
            params = []
            if role is not None:
                fields.append("role = ?")
                params.append(role.value)
            if organization_id is not None:
                fields.append("organization_id = ?")
                params.append(organization_id)
            params.append(username)
            sql = f"UPDATE users SET {', '.join(fields)} WHERE username = ?"
            cur = conn.execute(sql, tuple(params))
            conn.commit()
            return cur.rowcount > 0
_store: UserStore | None = None
_store_lock = threading.Lock()


def get_user_store() -> UserStore:
    """Get the global UserStore singleton instance.

    Returns:
        The module-level UserStore instance.
    """
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = UserStore()
    return _store
