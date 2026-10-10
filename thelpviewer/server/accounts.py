"""Admin-created accounts with one-time Passkey enrollment and server sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


CEREMONY_LIFETIME = 300
INVITATION_LIFETIME = 86400
REGISTRATION_LIFETIME = 3600
SESSION_LIFETIME = 30 * 86400
_EMAIL = re.compile(r"^[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+\.[^@\s\x00-\x1f\x7f]+$")
_REGISTRATION_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _profile_names(first_name: str | None, last_name: str | None, nickname: str | None) -> tuple:
    names = tuple(value.strip() if value is not None else None for value in (first_name, last_name, nickname))
    if any(value is not None and (len(value) > 100 or any(ord(char) < 32 or ord(char) == 127 for char in value))
           for value in names):
        raise AccountError("Profile names must be at most 100 characters without control characters")
    return names


def _profile_label(account: sqlite3.Row, names: tuple) -> str:
    first, last, nickname = (value if value is not None else account[field]
                             for field, value in zip(("first_name", "last_name", "nickname"), names))
    return (nickname or " ".join(value for value in (first, last) if value)
            or account["display_name"] or account["username"])[:100]


def _new_registration_token() -> str:
    characters = "".join(secrets.choice(_REGISTRATION_ALPHABET) for _ in range(25))
    return "-".join(characters[index:index + 5] for index in range(0, 25, 5))


def _registration_token_hash(token: str) -> str:
    supplied = token.strip().upper()
    compact = supplied.replace("-", "")
    valid_characters = len(compact) == 25 and all(char in _REGISTRATION_ALPHABET for char in compact)
    valid_groups = supplied == compact or supplied == "-".join(
        compact[index:index + 5] for index in range(0, 25, 5)
    )
    if not valid_characters or not valid_groups:
        raise AccountError("Invalid registration token format")
    canonical = "-".join(compact[index:index + 5] for index in range(0, 25, 5))
    return _token_hash(canonical)


class AccountError(ValueError):
    """An account ceremony failed without exposing its private details."""


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountStore:
    def __init__(self, state_dir: Path):
        self.path = state_dir / "accounts.sqlite3"

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL, email TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'member', active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS invitations (
                token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS credentials (
                credential_id BLOB PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
                public_key BLOB NOT NULL, sign_count INTEGER NOT NULL,
                device_type TEXT NOT NULL DEFAULT '', backed_up INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS ceremonies (
                id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
                kind TEXT NOT NULL, challenge BLOB NOT NULL,
                invitation_hash TEXT, expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS registration_tokens (
                token_hash TEXT PRIMARY KEY, issuer_id TEXT REFERENCES accounts(id),
                bootstrap INTEGER NOT NULL DEFAULT 0, expires_at INTEGER NOT NULL,
                token_ciphertext BLOB
            );
            CREATE TABLE IF NOT EXISTS pending_registrations (
                id TEXT PRIMARY KEY, account_id TEXT NOT NULL,
                token_hash TEXT NOT NULL, challenge BLOB NOT NULL,
                display_name TEXT NOT NULL, email TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            );
        """)
        connection.execute("BEGIN IMMEDIATE")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
        if "email" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        for field in ("first_name", "last_name", "nickname"):
            if field not in columns:
                connection.execute(f"ALTER TABLE accounts ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")
        connection.execute(
            "UPDATE accounts SET display_name='Admin' WHERE username='local-development-admin' "
            "AND display_name='Local Administrator' AND first_name='' AND last_name='' AND nickname=''"
        )
        if "disk_capacity_mb" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN disk_capacity_mb INTEGER")
        if "protected_admin" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN protected_admin INTEGER NOT NULL DEFAULT 0")
            # Existing installations used the first account as their bootstrap admin.
            # Persist its identity once, independently of later sorting/profile edits.
            connection.execute("UPDATE accounts SET protected_admin=1 WHERE id=(SELECT id FROM accounts ORDER BY rowid LIMIT 1)")
        if "role" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'member'")
            connection.execute(
                "UPDATE accounts SET role = 'admin' WHERE id = "
                "(SELECT id FROM accounts ORDER BY rowid LIMIT 1)"
            )
        registration_columns = {row[1] for row in connection.execute("PRAGMA table_info(registration_tokens)")}
        if "token_ciphertext" not in registration_columns:
            connection.execute("ALTER TABLE registration_tokens ADD COLUMN token_ciphertext BLOB")
        pending_columns = {row[1] for row in connection.execute("PRAGMA table_info(pending_registrations)")}
        for field in ("first_name", "last_name", "nickname"):
            if field not in pending_columns:
                connection.execute(f"ALTER TABLE pending_registrations ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS accounts_email ON accounts(email COLLATE NOCASE) WHERE email != ''")
        connection.commit()
        return connection

    def _registration_cipher(self, *, create: bool = False) -> Fernet | None:
        key_path = self.path.parent / "registration-tokens.key"
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

    @staticmethod
    def _administrator(connection: sqlite3.Connection, session_token: str) -> str:
        issuer = connection.execute(
            "SELECT a.id FROM sessions s JOIN accounts a ON a.id = s.account_id "
            "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1 AND a.role = 'admin'",
            (_token_hash(session_token), int(time.time())),
        ).fetchone()
        if issuer is None:
            raise AccountError("Administrator sign-in required")
        return issuer[0]

    def bootstrap_token(self) -> str | None:
        """Rotate the first-admin token at startup; return it for the server log."""
        with closing(self._connect()) as connection, connection:
            if connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
                return None
            token = _new_registration_token()
            connection.execute("DELETE FROM registration_tokens WHERE bootstrap = 1")
            connection.execute(
                "INSERT INTO registration_tokens(token_hash, bootstrap, expires_at) VALUES (?, 1, ?)",
                (_registration_token_hash(token), int(time.time()) + REGISTRATION_LIFETIME),
            )
            return token

    def issue_registration_token(self, session_token: str) -> str:
        token = _new_registration_token()
        with closing(self._connect()) as connection, connection:
            issuer_id = self._administrator(connection, session_token)
            cipher = self._registration_cipher(create=True)
            connection.execute(
                "INSERT INTO registration_tokens(token_hash, issuer_id, expires_at, token_ciphertext) "
                "VALUES (?, ?, ?, ?)",
                (_registration_token_hash(token), issuer_id, int(time.time()) + REGISTRATION_LIFETIME,
                 cipher.encrypt(token.encode("ascii"))),
            )
        return token

    def list_registration_tokens(self, session_token: str) -> list[dict[str, str | int | None]]:
        with closing(self._connect()) as connection, connection:
            self._administrator(connection, session_token)
            connection.execute("DELETE FROM registration_tokens WHERE expires_at <= ?", (int(time.time()),))
            rows = connection.execute(
                "SELECT token_hash, token_ciphertext, expires_at FROM registration_tokens "
                "WHERE bootstrap = 0 AND expires_at > ? ORDER BY expires_at DESC",
                (int(time.time()),),
            ).fetchall()
        cipher = self._registration_cipher() if any(row["token_ciphertext"] for row in rows) else None
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

    def delete_registration_token(self, session_token: str, token_hash: str) -> None:
        with closing(self._connect()) as connection, connection:
            self._administrator(connection, session_token)
            deleted = connection.execute(
                "DELETE FROM registration_tokens WHERE token_hash = ? AND bootstrap = 0 AND expires_at > ?",
                (token_hash, int(time.time())),
            )
            if deleted.rowcount != 1:
                raise AccountError("Registration token is no longer active")

    @staticmethod
    def _registration_token(connection: sqlite3.Connection, token: str):
        row = connection.execute(
            "SELECT token_hash, bootstrap, issuer_id FROM registration_tokens "
            "WHERE token_hash = ? AND expires_at > ?",
            (_registration_token_hash(token), int(time.time())),
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

    def new_registration_options(self, display_name: str, email: str, token: str,
                                 rp_id: str, rp_name: str, *, first_name: str | None = None,
                                 last_name: str | None = None, nickname: str | None = None) -> dict:
        from webauthn import generate_registration_options
        from webauthn.helpers import options_to_json
        from webauthn.helpers.structs import AuthenticatorSelectionCriteria, ResidentKeyRequirement, UserVerificationRequirement

        display_name = display_name.strip()
        email = email.strip().casefold()
        names = tuple(value or "" for value in _profile_names(first_name, last_name, nickname))
        if not 1 <= len(display_name) <= 100 or not _EMAIL.fullmatch(email) or len(email) > 254:
            raise AccountError("Enter a valid name and email address")
        display_name = names[2] or " ".join(value for value in names[:2] if value)[:100] or display_name
        with closing(self._connect()) as connection, connection:
            existing = connection.execute(
                "SELECT first_name, last_name, nickname FROM accounts WHERE email=? COLLATE NOCASE OR username=?",
                (email, email),
            ).fetchone()
            if existing:
                # An administrator-created account enrolls its own Passkey,
                # using the existing account-bound invitation, not a new account.
                result = self.registration_options(email, token.strip().upper(), rp_id, rp_name)
                return {**result, "enrollment": True, "profile": dict(existing)}
            registration = self._registration_token(connection, token)
            account_id = uuid.uuid4().hex
            options = generate_registration_options(
                rp_id=rp_id, rp_name=rp_name, user_id=bytes.fromhex(account_id),
                user_name=email, user_display_name=display_name,
                authenticator_selection=AuthenticatorSelectionCriteria(
                    resident_key=ResidentKeyRequirement.REQUIRED,
                    user_verification=UserVerificationRequirement.REQUIRED,
                ),
            )
            ceremony_id = secrets.token_urlsafe(24)
            connection.execute(
                "INSERT INTO pending_registrations"
                "(id, account_id, token_hash, challenge, display_name, email, expires_at, first_name, last_name, nickname) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ceremony_id, account_id, registration["token_hash"], options.challenge,
                 display_name, email, int(time.time()) + CEREMONY_LIFETIME, *names),
            )
        return {"ceremony_id": ceremony_id, "options": json.loads(options_to_json(options))}

    def verify_new_registration(self, ceremony_id: str, credential: dict, rp_id: str, origin: str) -> str:
        from webauthn import verify_registration_response

        if len(json.dumps(credential)) > 16384:
            raise AccountError("Passkey response is too large")
        with closing(self._connect()) as connection, connection:
            pending = connection.execute(
                "DELETE FROM pending_registrations WHERE id = ? AND expires_at > ? "
                "RETURNING account_id, token_hash, challenge, display_name, email, first_name, last_name, nickname",
                (ceremony_id, int(time.time())),
            ).fetchone()
            if pending is None:
                raise AccountError("Registration request expired; please try again")
            connection.commit()
            registration = connection.execute(
                "SELECT token_hash, bootstrap, issuer_id FROM registration_tokens "
                "WHERE token_hash = ? AND expires_at > ?",
                (pending["token_hash"], int(time.time())),
            ).fetchone()
            if registration is None:
                raise AccountError("Registration token has expired")
            try:
                result = verify_registration_response(
                    credential=credential, expected_challenge=bytes(pending["challenge"]),
                    expected_rp_id=rp_id, expected_origin=origin, require_user_verification=True,
                )
            except Exception:
                raise AccountError("Passkey verification failed") from None
            if registration["bootstrap"] and connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
                raise AccountError("First administrator already exists")
            if not registration["bootstrap"] and not connection.execute(
                "SELECT 1 FROM accounts WHERE id = ? AND active = 1 AND role = 'admin'",
                (registration["issuer_id"],),
            ).fetchone():
                raise AccountError("Registration token is no longer valid")
            consumed = connection.execute(
                "DELETE FROM registration_tokens WHERE token_hash = ? AND expires_at > ? RETURNING token_hash",
                (pending["token_hash"], int(time.time())),
            ).fetchone()
            if consumed is None:
                raise AccountError("Registration token has already been used")
            try:
                connection.execute(
                    "INSERT INTO accounts(id, username, display_name, email, role, protected_admin, first_name, last_name, nickname) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (pending["account_id"], pending["email"], pending["display_name"],
                     pending["email"], "admin" if registration["bootstrap"] else "member", int(bool(registration["bootstrap"])),
                     pending["first_name"], pending["last_name"], pending["nickname"]),
                )
                connection.execute(
                    "INSERT INTO credentials(credential_id, account_id, public_key, sign_count, device_type, backed_up) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (result.credential_id, pending["account_id"], result.credential_public_key,
                     result.sign_count, str(result.credential_device_type), int(result.credential_backed_up)),
                )
            except sqlite3.IntegrityError:
                raise AccountError("Account or Passkey is already registered") from None
            return self._new_session(connection, pending["account_id"])

    def create_user(self, username: str, display_name: str = "") -> str:
        username = username.strip()
        if not 1 <= len(username) <= 64 or not all(char.isalnum() or char in "._-" for char in username):
            raise AccountError("Username must contain 1–64 letters, digits, dots, underscores or dashes")
        account_id = uuid.uuid4().hex
        with closing(self._connect()) as connection, connection:
            first = not connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone()
            try:
                connection.execute(
                    "INSERT INTO accounts(id, username, display_name, role, protected_admin) VALUES (?, ?, ?, ?, ?)",
                    (account_id, username, (display_name.strip() or username)[:100],
                     "admin" if first else "member", int(first)),
                )
            except sqlite3.IntegrityError:
                raise AccountError("Account already exists") from None
        return self.issue_invitation(username)

    def development_session(self) -> str:
        """Issue a normal session in the separate, opt-in development account store."""
        with closing(self._connect()) as connection, connection:
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
            return self._new_session(connection, account["id"])

    def issue_invitation(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with closing(self._connect()) as connection, connection:
            account = connection.execute(
                "SELECT id FROM accounts WHERE username = ? AND active = 1", (username.strip(),)
            ).fetchone()
            if account is None:
                raise AccountError("Account does not exist")
            connection.execute("DELETE FROM invitations WHERE account_id = ?", (account["id"],))
            connection.execute(
                "INSERT INTO invitations(token_hash, account_id, expires_at) VALUES (?, ?, ?)",
                (_token_hash(token), account["id"], now + INVITATION_LIFETIME),
            )
        return token

    def _account_for_invitation(self, connection: sqlite3.Connection, username: str, token: str):
        digest = _token_hash(token)
        row = connection.execute(
            "SELECT a.id, a.username, a.display_name FROM accounts a "
            "JOIN invitations i ON i.account_id = a.id "
            "WHERE a.username = ? AND a.active = 1 AND i.token_hash = ? AND i.expires_at > ?",
            (username.strip(), digest, int(time.time())),
        ).fetchone()
        if row is None:
            raise AccountError("Invalid or expired enrollment token")
        return row, digest

    def registration_options(self, username: str, token: str, rp_id: str, rp_name: str) -> dict:
        from webauthn import generate_registration_options
        from webauthn.helpers import options_to_json
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
            ResidentKeyRequirement, UserVerificationRequirement,
        )

        with closing(self._connect()) as connection, connection:
            account, digest = self._account_for_invitation(connection, username, token)
            existing = connection.execute(
                "SELECT credential_id FROM credentials WHERE account_id = ?", (account["id"],)
            ).fetchall()
            options = generate_registration_options(
                rp_id=rp_id, rp_name=rp_name, user_id=bytes.fromhex(account["id"]),
                user_name=account["username"], user_display_name=account["display_name"],
                authenticator_selection=AuthenticatorSelectionCriteria(
                    resident_key=ResidentKeyRequirement.REQUIRED,
                    user_verification=UserVerificationRequirement.REQUIRED,
                ),
                exclude_credentials=[PublicKeyCredentialDescriptor(id=bytes(row[0])) for row in existing],
            )
            ceremony_id = secrets.token_urlsafe(24)
            connection.execute(
                "INSERT INTO ceremonies(id, account_id, kind, challenge, invitation_hash, expires_at) "
                "VALUES (?, ?, 'register', ?, ?, ?)",
                (ceremony_id, account["id"], options.challenge, digest, int(time.time()) + CEREMONY_LIFETIME),
            )
        return {"ceremony_id": ceremony_id, "options": json.loads(options_to_json(options))}

    def _consume_ceremony(self, connection: sqlite3.Connection, ceremony_id: str, kind: str):
        row = connection.execute(
            "DELETE FROM ceremonies WHERE id = ? AND kind = ? AND expires_at > ? "
            "RETURNING account_id, challenge, invitation_hash",
            (ceremony_id, kind, int(time.time())),
        ).fetchone()
        if row is None:
            raise AccountError("Authentication request expired; please try again")
        connection.commit()
        return row

    def _new_session(self, connection: sqlite3.Connection, account_id: str) -> str:
        token = secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO sessions(token_hash, account_id, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), account_id, int(time.time()) + SESSION_LIFETIME),
        )
        return token

    def verify_registration(self, ceremony_id: str, credential: dict, rp_id: str, origin: str) -> str:
        from webauthn import verify_registration_response

        if len(json.dumps(credential)) > 16384:
            raise AccountError("Passkey response is too large")
        with closing(self._connect()) as connection, connection:
            ceremony = self._consume_ceremony(connection, ceremony_id, "register")
            invitation = connection.execute(
                "SELECT 1 FROM invitations i JOIN accounts a ON a.id=i.account_id "
                "WHERE i.token_hash = ? AND i.account_id = ? AND i.expires_at > ? AND a.active=1",
                (ceremony["invitation_hash"], ceremony["account_id"], int(time.time())),
            ).fetchone()
            if invitation is None:
                raise AccountError("Enrollment token has expired")
            try:
                result = verify_registration_response(
                    credential=credential, expected_challenge=bytes(ceremony["challenge"]),
                    expected_rp_id=rp_id, expected_origin=origin, require_user_verification=True,
                )
            except Exception:
                raise AccountError("Passkey verification failed") from None
            try:
                connection.execute(
                    "INSERT INTO credentials(credential_id, account_id, public_key, sign_count, device_type, backed_up) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (result.credential_id, ceremony["account_id"], result.credential_public_key,
                     result.sign_count, str(result.credential_device_type), int(result.credential_backed_up)),
                )
            except sqlite3.IntegrityError:
                raise AccountError("Passkey is already registered") from None
            connection.execute("DELETE FROM invitations WHERE token_hash = ?", (ceremony["invitation_hash"],))
            return self._new_session(connection, ceremony["account_id"])

    def authentication_options(self, username: str, rp_id: str) -> dict:
        from webauthn import generate_authentication_options
        from webauthn.helpers import options_to_json
        from webauthn.helpers.structs import PublicKeyCredentialDescriptor, UserVerificationRequirement

        with closing(self._connect()) as connection, connection:
            account = connection.execute(
                "SELECT id FROM accounts WHERE (username = ? OR email = ? COLLATE NOCASE) AND active = 1",
                (username.strip(), username.strip()),
            ).fetchone()
            if account is None:
                raise AccountError("Account or Passkey was not found")
            credentials = connection.execute(
                "SELECT credential_id FROM credentials WHERE account_id = ?", (account["id"],)
            ).fetchall()
            if not credentials:
                raise AccountError("Account or Passkey was not found")
            options = generate_authentication_options(
                rp_id=rp_id,
                allow_credentials=[PublicKeyCredentialDescriptor(id=bytes(row[0])) for row in credentials],
                user_verification=UserVerificationRequirement.REQUIRED,
            )
            ceremony_id = secrets.token_urlsafe(24)
            connection.execute(
                "INSERT INTO ceremonies(id, account_id, kind, challenge, expires_at) "
                "VALUES (?, ?, 'authenticate', ?, ?)",
                (ceremony_id, account["id"], options.challenge, int(time.time()) + CEREMONY_LIFETIME),
            )
        return {"ceremony_id": ceremony_id, "options": json.loads(options_to_json(options))}

    def verify_authentication(self, ceremony_id: str, credential: dict, rp_id: str, origin: str) -> str:
        from webauthn import base64url_to_bytes, verify_authentication_response

        if len(json.dumps(credential)) > 16384:
            raise AccountError("Passkey response is too large")
        with closing(self._connect()) as connection, connection:
            ceremony = self._consume_ceremony(connection, ceremony_id, "authenticate")
            try:
                credential_id = base64url_to_bytes(credential["id"])
            except (KeyError, ValueError, TypeError):
                raise AccountError("Passkey verification failed") from None
            stored = connection.execute(
                "SELECT public_key, sign_count FROM credentials WHERE credential_id = ? AND account_id = ?",
                (credential_id, ceremony["account_id"]),
            ).fetchone()
            if stored is None:
                raise AccountError("Passkey verification failed")
            try:
                result = verify_authentication_response(
                    credential=credential, expected_challenge=bytes(ceremony["challenge"]),
                    expected_rp_id=rp_id, expected_origin=origin,
                    credential_public_key=bytes(stored["public_key"]),
                    credential_current_sign_count=stored["sign_count"],
                    require_user_verification=True,
                )
            except Exception:
                raise AccountError("Passkey verification failed") from None
            connection.execute(
                "UPDATE credentials SET sign_count = ?, device_type = ?, backed_up = ? WHERE credential_id = ?",
                (result.new_sign_count, str(result.credential_device_type),
                 int(result.credential_backed_up), credential_id),
            )
            return self._new_session(connection, ceremony["account_id"])

    def session_user(self, token: str) -> dict[str, str] | None:
        if not token:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT a.username, a.display_name, a.email, a.role, a.first_name, a.last_name, a.nickname FROM sessions s "
                "JOIN accounts a ON a.id = s.account_id "
                "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1",
                (_token_hash(token), int(time.time())),
            ).fetchone()
        return None if row is None else dict(row)

    def update_profile(self, token: str, email: str, *, first_name: str | None = None,
                       last_name: str | None = None, nickname: str | None = None) -> dict[str, str]:
        """Edit only the session owner's profile, preserving ID, role and Passkeys."""
        email = email.strip().casefold()
        names = _profile_names(first_name, last_name, nickname)
        with closing(self._connect()) as connection, connection:
            account = connection.execute(
                "SELECT a.id, a.username, a.display_name, a.email, a.first_name, a.last_name, a.nickname "
                "FROM sessions s JOIN accounts a ON a.id = s.account_id "
                "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1",
                (_token_hash(token), int(time.time())),
            ).fetchone()
            if account is None:
                raise AccountError("Sign-in required")
            display_name = _profile_label(account, names)
            if len(email) > 254 or not _EMAIL.fullmatch(email):
                raise AccountError("Enter a valid email address")
            if connection.execute(
                "SELECT 1 FROM accounts WHERE id != ? AND (email = ? COLLATE NOCASE OR username = ?)",
                (account["id"], email, email),
            ).fetchone():
                raise AccountError("Email address is already registered")
            try:
                connection.execute(
                    "UPDATE accounts SET display_name=?, email=?, first_name=COALESCE(?,first_name), "
                    "last_name=COALESCE(?,last_name), nickname=COALESCE(?,nickname) WHERE id=?",
                    (display_name, email, *names, account["id"]),
                )
            except sqlite3.IntegrityError:
                raise AccountError("Email address is already registered") from None
        return self.session_user(token)

    def disk_capacity(self, account_id: str) -> int | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT disk_capacity_mb FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return row[0] if row else None

    def list_users(self, token: str) -> list[dict]:
        with closing(self._connect()) as connection:
            self._administrator(connection, token)
            rows = connection.execute(
                "SELECT id, username, display_name, email, first_name, last_name, nickname, role, active, disk_capacity_mb, protected_admin "
                "FROM accounts ORDER BY display_name COLLATE NOCASE, username"
            ).fetchall()
        return [{**dict(row), "active": bool(row["active"]), "protected_admin": bool(row["protected_admin"])} for row in rows]

    def create_managed_user(self, token: str, email: str, first_name: str = "",
                            last_name: str = "", nickname: str = "") -> dict:
        """Create a member and a bound one-hour invitation without issuing a session."""
        email = email.strip().casefold()
        names = _profile_names(first_name, last_name, nickname)
        if not _EMAIL.fullmatch(email) or len(email) > 254:
            raise AccountError("Enter a valid email address")
        if not names[0] and not names[2]:
            raise AccountError("Enter first name or nickname")
        display_name = (names[2] or " ".join(value for value in names[:2] if value))[:100]
        account_id = uuid.uuid4().hex
        invitation = _new_registration_token()
        expires_at = int(time.time()) + REGISTRATION_LIFETIME
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            self._administrator(connection, token)
            if connection.execute(
                "SELECT 1 FROM accounts WHERE email=? COLLATE NOCASE OR username=?", (email, email),
            ).fetchone():
                raise AccountError("Email address is already registered")
            try:
                connection.execute(
                    "INSERT INTO accounts(id,username,email,display_name,first_name,last_name,nickname,role) "
                    "VALUES (?,?,?,?,?,?,?,'member')", (account_id, email, email, display_name, *names),
                )
                connection.execute("INSERT INTO invitations(token_hash,account_id,expires_at) VALUES (?,?,?)",
                                   (_token_hash(invitation), account_id, expires_at))
            except sqlite3.IntegrityError:
                raise AccountError("Email address is already registered") from None
            row = connection.execute(
                "SELECT id,username,email,display_name,first_name,last_name,nickname,role,active,disk_capacity_mb,protected_admin "
                "FROM accounts WHERE id=?", (account_id,),
            ).fetchone()
        return {"user": {**dict(row), "active": bool(row["active"]), "protected_admin": bool(row["protected_admin"])},
                "invitation": {"token": invitation, "expires_at": expires_at}}

    def update_user(self, token: str, account_id: str, email: str,
                    role: str, active: bool, disk_capacity_mb: int | None, *, first_name: str | None = None,
                    last_name: str | None = None, nickname: str | None = None) -> dict:
        """Administrative profile edits never replace IDs, Passkeys or DOS data."""
        email = email.strip().casefold()
        names = _profile_names(first_name, last_name, nickname)
        if len(email) > 254 or (email and not _EMAIL.fullmatch(email)):
            raise AccountError("Enter a valid email address")
        if role not in {"admin", "member"} or type(active) is not bool:
            raise AccountError("Invalid account role or state")
        if disk_capacity_mb is not None and (type(disk_capacity_mb) is not int or not 1 <= disk_capacity_mb <= 256):
            raise AccountError("Disk capacity must be 1–256 MiB or the server default")
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            self._administrator(connection, token)
            account = connection.execute(
                "SELECT username, display_name, first_name, last_name, nickname, role, active, protected_admin "
                "FROM accounts WHERE id = ?", (account_id,),
            ).fetchone()
            if account is None:
                raise AccountError("Account not found")
            display_name = _profile_label(account, names)
            if account["protected_admin"] and (role != "admin" or not active):
                raise AccountError("The founding administrator cannot be disabled or demoted")
            if account["role"] == "admin" and account["active"] and (role != "admin" or not active):
                count = connection.execute("SELECT COUNT(*) FROM accounts WHERE active = 1 AND role = 'admin'").fetchone()[0]
                if count <= 1:
                    raise AccountError("The last active administrator cannot be disabled or demoted")
            if email and connection.execute(
                "SELECT 1 FROM accounts WHERE id != ? AND (email = ? COLLATE NOCASE OR username = ?)",
                (account_id, email, email),
            ).fetchone():
                raise AccountError("Email address is already registered")
            try:
                connection.execute(
                    "UPDATE accounts SET display_name=?, email=?, role=?, active=?, disk_capacity_mb=?, "
                    "first_name=COALESCE(?,first_name), last_name=COALESCE(?,last_name), "
                    "nickname=COALESCE(?,nickname) WHERE id=?",
                    (display_name, email, role, int(active), disk_capacity_mb, *names, account_id),
                )
            except sqlite3.IntegrityError:
                raise AccountError("Email address is already registered") from None
            if not active:
                connection.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
                connection.execute("DELETE FROM ceremonies WHERE account_id=?", (account_id,))
                connection.execute("DELETE FROM invitations WHERE account_id=?", (account_id,))
            row = connection.execute(
                "SELECT id, username, display_name, email, first_name, last_name, nickname, role, active, disk_capacity_mb, protected_admin FROM accounts WHERE id=?",
                (account_id,),
            ).fetchone()
        return {**dict(row), "active": bool(row["active"]), "protected_admin": bool(row["protected_admin"])}

    def session_account_id(self, token: str) -> str | None:
        """Resolve a private storage owner without exposing account IDs in API sessions."""
        if not token:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT a.id FROM sessions s JOIN accounts a ON a.id=s.account_id "
                "WHERE s.token_hash=? AND s.expires_at>? AND a.active=1",
                (_token_hash(token), int(time.time())),
            ).fetchone()
        return row[0] if row else None

    def logout(self, token: str) -> None:
        if token:
            with closing(self._connect()) as connection, connection:
                connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def main() -> None:
    parser = argparse.ArgumentParser(description="Admin-managed THelpViewer accounts")
    subcommands = parser.add_subparsers(dest="command", required=True)
    create = subcommands.add_parser("create", help="Create account and one-time Passkey enrollment token")
    create.add_argument("username")
    create.add_argument("--name", default="")
    invite = subcommands.add_parser("invite", help="Replace an account's enrollment token")
    invite.add_argument("username")
    args = parser.parse_args()
    store = AccountStore(Path(os.environ.get("THELP_STATE_DIR", "var")))
    try:
        token = (store.create_user(args.username, args.name) if args.command == "create"
                 else store.issue_invitation(args.username))
    except AccountError as error:
        parser.error(str(error))
    print(f"Account: {args.username}\nOne-time enrollment token (24 hours): {token}")
    print("Give this token to the user privately; it will not be shown again.")


if __name__ == "__main__":
    main()
