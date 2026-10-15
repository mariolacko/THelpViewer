"""One-use enrollment invitations and encrypted one-hour registration tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING
from contextlib import closing
import os
import secrets
import sqlite3
import time

from cryptography.fernet import Fernet, InvalidToken

from .common import AccountError, token_hash
from .sessions import administrator

INVITATION_LIFETIME = 86400
REGISTRATION_LIFETIME = 3600
_REGISTRATION_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


if TYPE_CHECKING:
    from .store import AccountStore


def new_registration_token() -> str:
    characters = "".join(secrets.choice(_REGISTRATION_ALPHABET) for _ in range(25))
    return "-".join(characters[index:index + 5] for index in range(0, 25, 5))


def registration_token_hash(token: str) -> str:
    supplied = token.strip().upper()
    compact = supplied.replace("-", "")
    valid_characters = len(compact) == 25 and all(char in _REGISTRATION_ALPHABET for char in compact)
    valid_groups = supplied == compact or supplied == "-".join(
        compact[index:index + 5] for index in range(0, 25, 5)
    )
    if not valid_characters or not valid_groups:
        raise AccountError("Invalid registration token format")
    canonical = "-".join(compact[index:index + 5] for index in range(0, 25, 5))
    return token_hash(canonical)


def registration_cipher(store: AccountStore, *, create: bool = False) -> Fernet | None:
    key_path = store.path.parent / "registration-tokens.key"
    if create:
        try:
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(Fernet.generate_key())
    if not key_path.is_file():
        return None
    return Fernet(key_path.read_bytes())


def bootstrap_token(store: AccountStore) -> str | None:
    """Rotate the first-admin token at startup; return it for the server log."""
    with closing(store._connect()) as connection, connection:
        if connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
            return None
        token = new_registration_token()
        connection.execute("DELETE FROM registration_tokens WHERE bootstrap = 1")
        connection.execute(
            "INSERT INTO registration_tokens(token_hash, bootstrap, expires_at) VALUES (?, 1, ?)",
            (registration_token_hash(token), int(time.time()) + REGISTRATION_LIFETIME),
        )
        return token


def issue_registration_token(store: AccountStore, session_token: str) -> str:
    token = new_registration_token()
    with closing(store._connect()) as connection, connection:
        issuer_id = administrator(connection, session_token)
        cipher = registration_cipher(store, create=True)
        connection.execute(
            "INSERT INTO registration_tokens(token_hash, issuer_id, expires_at, token_ciphertext) "
            "VALUES (?, ?, ?, ?)",
            (registration_token_hash(token), issuer_id, int(time.time()) + REGISTRATION_LIFETIME,
             cipher.encrypt(token.encode("ascii"))),
        )
    return token


def list_registration_tokens(store: AccountStore, session_token: str) -> list[dict[str, str | int | None]]:
    with closing(store._connect()) as connection, connection:
        administrator(connection, session_token)
        connection.execute("DELETE FROM registration_tokens WHERE expires_at <= ?", (int(time.time()),))
        rows = connection.execute(
            "SELECT token_hash, token_ciphertext, expires_at FROM registration_tokens "
            "WHERE bootstrap = 0 AND expires_at > ? ORDER BY expires_at DESC",
            (int(time.time()),),
        ).fetchall()
    cipher = registration_cipher(store) if any(row["token_ciphertext"] for row in rows) else None
    tokens = []
    for row in rows:
        value = None
        if cipher and row["token_ciphertext"]:
            try:
                value = cipher.decrypt(bytes(row["token_ciphertext"])).decode("ascii")
            except (InvalidToken, UnicodeDecodeError):
                pass
        tokens.append({"id": row["token_hash"], "token": value, "expires_at": row["expires_at"]})
    return tokens


def delete_registration_token(store: AccountStore, session_token: str, token_hash: str) -> None:
    with closing(store._connect()) as connection, connection:
        administrator(connection, session_token)
        deleted = connection.execute(
            "DELETE FROM registration_tokens WHERE token_hash = ? AND bootstrap = 0 AND expires_at > ?",
            (token_hash, int(time.time())),
        )
        if deleted.rowcount != 1:
            raise AccountError("Registration token is no longer active")


def registration_token(connection: sqlite3.Connection, token: str):
    row = connection.execute(
        "SELECT token_hash, bootstrap, issuer_id FROM registration_tokens "
        "WHERE token_hash = ? AND expires_at > ?",
        (registration_token_hash(token), int(time.time())),
    ).fetchone()
    if row is None:
        raise AccountError("Invalid or expired registration token")
    if row["bootstrap"]:
        if connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
            raise AccountError("First administrator already exists")
    elif not connection.execute(
        "SELECT 1 FROM accounts WHERE id = ? AND active = 1 AND role = 'admin'", (row["issuer_id"],)
    ).fetchone():
        raise AccountError("Registration token is no longer valid")
    return row


def issue_invitation(store: AccountStore, username: str) -> str:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with closing(store._connect()) as connection, connection:
        account = connection.execute(
            "SELECT id FROM accounts WHERE username = ? AND active = 1", (username.strip(),)
        ).fetchone()
        if account is None:
            raise AccountError("Account does not exist")
        connection.execute("DELETE FROM invitations WHERE account_id = ?", (account["id"],))
        connection.execute(
            "INSERT INTO invitations(token_hash, account_id, expires_at) VALUES (?, ?, ?)",
            (token_hash(token), account["id"], now + INVITATION_LIFETIME),
        )
    return token


def account_for_invitation(connection: sqlite3.Connection, username: str, token: str):
    digest = token_hash(token)
    row = connection.execute(
        "SELECT a.id, a.username, a.display_name FROM accounts a "
        "JOIN invitations i ON i.account_id = a.id "
        "WHERE a.username = ? AND a.active = 1 AND i.token_hash = ? AND i.expires_at > ?",
        (username.strip(), digest, int(time.time())),
    ).fetchone()
    if row is None:
        raise AccountError("Invalid or expired enrollment token")
    return row, digest
