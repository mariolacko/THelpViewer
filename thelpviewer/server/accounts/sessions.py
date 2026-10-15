"""Session creation, active-account lookup and administrator authorization."""

from __future__ import annotations

from typing import TYPE_CHECKING
from contextlib import closing
import secrets
import sqlite3
import time
import uuid

from .common import AccountError, token_hash

SESSION_LIFETIME = 30 * 86400


if TYPE_CHECKING:
    from .store import AccountStore


def administrator(connection: sqlite3.Connection, session_token: str) -> str:
    issuer = connection.execute(
        "SELECT a.id FROM sessions s JOIN accounts a ON a.id = s.account_id "
        "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1 AND a.role = 'admin'",
        (token_hash(session_token), int(time.time())),
    ).fetchone()
    if issuer is None:
        raise AccountError("Administrator sign-in required")
    return issuer[0]


def owner(connection: sqlite3.Connection, token: str, *, recent_passkey: bool = False):
    row = connection.execute(
        "SELECT a.id, a.username, a.email, a.display_name, a.password_hash, s.verified_at, s.auth_method "
        "FROM sessions s JOIN accounts a ON a.id=s.account_id "
        "WHERE s.token_hash=? AND s.expires_at>? AND a.active=1",
        (token_hash(token), int(time.time())),
    ).fetchone()
    if row is None:
        raise AccountError("Sign-in required")
    if recent_passkey and (row["auth_method"] not in {"passkey", "development"}
                           or row["verified_at"] <= int(time.time()) - 300):
        raise AccountError("Confirm your identity with a Passkey before changing sign-in methods")
    return row


def new_session(connection: sqlite3.Connection, account_id: str, *, auth_method: str = "passkey") -> str:
    token = secrets.token_urlsafe(32)
    connection.execute(
        "INSERT INTO sessions(token_hash, account_id, expires_at, verified_at, auth_method) VALUES (?, ?, ?, ?, ?)",
        (token_hash(token), account_id, int(time.time()) + SESSION_LIFETIME, int(time.time()), auth_method),
    )
    return token


def development_session(store: AccountStore) -> str:
    """Issue a normal session in the separate, opt-in development account store."""
    with closing(store._connect()) as connection, connection:
        connection.execute(
            "INSERT INTO accounts(id, username, display_name, role, protected_admin) VALUES (?, ?, ?, 'admin', ?) "
            "ON CONFLICT(username) DO NOTHING",
            (uuid.uuid4().hex, "local-development-admin", "Admin",
             int(not connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone())),
        )
        account = connection.execute(
            "SELECT id FROM accounts WHERE username = 'local-development-admin' "
            "AND active = 1 AND role = 'admin'"
        ).fetchone()
        if account is None:
            raise AccountError("Local development administrator is disabled")
        return new_session(connection, account["id"], auth_method="development")


def session_user(store: AccountStore, token: str) -> dict[str, str] | None:
    if not token:
        return None
    with closing(store._connect()) as connection:
        row = connection.execute(
            "SELECT a.username, a.display_name, a.email, a.role, a.first_name, a.last_name, a.nickname FROM sessions s "
            "JOIN accounts a ON a.id = s.account_id "
            "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1",
            (token_hash(token), int(time.time())),
        ).fetchone()
    return None if row is None else dict(row)


def session_account_id(store: AccountStore, token: str) -> str | None:
    """Resolve a private storage owner without exposing account IDs in API sessions."""
    if not token:
        return None
    with closing(store._connect()) as connection:
        row = connection.execute(
            "SELECT a.id FROM sessions s JOIN accounts a ON a.id=s.account_id "
            "WHERE s.token_hash=? AND s.expires_at>? AND a.active=1",
            (token_hash(token), int(time.time())),
        ).fetchone()
    return row[0] if row else None


def logout(store: AccountStore, token: str) -> None:
    if token:
        with closing(store._connect()) as connection, connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
