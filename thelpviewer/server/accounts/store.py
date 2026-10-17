"""SQLite account schema, profiles and administrative account management."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
import time
import uuid

from . import passkeys, passwords, registration, sessions
from .common import AccountError, EMAIL, profile_label, profile_names, token_hash
from .registration import REGISTRATION_LIFETIME, new_registration_token


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
        if "password_hash" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        credential_columns = {row[1] for row in connection.execute("PRAGMA table_info(credentials)")}
        for field, definition in (("name", "TEXT NOT NULL DEFAULT ''"),
                                  ("created_at", "INTEGER NOT NULL DEFAULT 0"),
                                  ("last_used_at", "INTEGER NOT NULL DEFAULT 0")):
            if field not in credential_columns:
                connection.execute(f"ALTER TABLE credentials ADD COLUMN {field} {definition}")
        session_columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        for field, definition in (("verified_at", "INTEGER NOT NULL DEFAULT 0"),
                                  ("auth_method", "TEXT NOT NULL DEFAULT ''")):
            if field not in session_columns:
                connection.execute(f"ALTER TABLE sessions ADD COLUMN {field} {definition}")
        if "created_at" not in session_columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0")
            # The old fixed-lifetime sessions have no activity timestamp. Give
            # still-valid sessions at most one day, without reviving expired ones.
            now = int(time.time())
            connection.execute("UPDATE sessions SET created_at=?, expires_at=MIN(expires_at, ?)",
                               (now, now + sessions.SESSION_LIFETIME))
        ceremony_columns = {row[1] for row in connection.execute("PRAGMA table_info(ceremonies)")}
        if "session_hash" not in ceremony_columns:
            connection.execute("ALTER TABLE ceremonies ADD COLUMN session_hash TEXT")
        connection.execute("CREATE TABLE IF NOT EXISTS password_attempts "
                           "(key TEXT PRIMARY KEY, started_at INTEGER NOT NULL, attempts INTEGER NOT NULL)")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS accounts_email ON accounts(email COLLATE NOCASE) WHERE email != ''")
        connection.commit()
        return connection

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

    def update_profile(self, token: str, email: str, *, first_name: str | None = None,
                       last_name: str | None = None, nickname: str | None = None) -> dict[str, str]:
        """Edit only the session owner's profile, preserving ID, role and Passkeys."""
        email = email.strip().casefold()
        names = profile_names(first_name, last_name, nickname)
        with closing(self._connect()) as connection, connection:
            account = connection.execute(
                "SELECT a.id, a.username, a.display_name, a.email, a.first_name, a.last_name, a.nickname "
                "FROM sessions s JOIN accounts a ON a.id = s.account_id "
                "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1",
                (token_hash(token), int(time.time())),
            ).fetchone()
            if account is None:
                raise AccountError("Sign-in required")
            display_name = profile_label(account, names)
            if len(email) > 254 or not EMAIL.fullmatch(email):
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
            sessions.administrator(connection, token)
            rows = connection.execute(
                "SELECT id, username, display_name, email, first_name, last_name, nickname, role, active, disk_capacity_mb, protected_admin "
                "FROM accounts ORDER BY display_name COLLATE NOCASE, username"
            ).fetchall()
        return [{**dict(row), "active": bool(row["active"]), "protected_admin": bool(row["protected_admin"])} for row in rows]

    def create_managed_user(self, token: str, email: str, first_name: str = "",
                            last_name: str = "", nickname: str = "") -> dict:
        """Create a member and a bound one-hour invitation without issuing a session."""
        email = email.strip().casefold()
        names = profile_names(first_name, last_name, nickname)
        if not EMAIL.fullmatch(email) or len(email) > 254:
            raise AccountError("Enter a valid email address")
        if not names[0] and not names[2]:
            raise AccountError("Enter first name or nickname")
        display_name = (names[2] or " ".join(value for value in names[:2] if value))[:100]
        account_id = uuid.uuid4().hex
        invitation = new_registration_token()
        expires_at = int(time.time()) + REGISTRATION_LIFETIME
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            sessions.administrator(connection, token)
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
                                   (token_hash(invitation), account_id, expires_at))
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
        names = profile_names(first_name, last_name, nickname)
        if len(email) > 254 or (email and not EMAIL.fullmatch(email)):
            raise AccountError("Enter a valid email address")
        if role not in {"admin", "member"} or type(active) is not bool:
            raise AccountError("Invalid account role or state")
        if disk_capacity_mb is not None and (type(disk_capacity_mb) is not int or not 1 <= disk_capacity_mb <= 256):
            raise AccountError("Disk capacity must be 1–256 MiB or the server default")
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            sessions.administrator(connection, token)
            account = connection.execute(
                "SELECT username, display_name, first_name, last_name, nickname, role, active, protected_admin "
                "FROM accounts WHERE id = ?", (account_id,),
            ).fetchone()
            if account is None:
                raise AccountError("Account not found")
            display_name = profile_label(account, names)
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

    def bootstrap_token(self) -> str | None:
        return registration.bootstrap_token(self)

    def issue_registration_token(self, session_token: str) -> str:
        return registration.issue_registration_token(self, session_token)

    def list_registration_tokens(self, session_token: str) -> list[dict[str, str | int | None]]:
        return registration.list_registration_tokens(self, session_token)

    def delete_registration_token(self, session_token: str, token_hash: str) -> None:
        return registration.delete_registration_token(self, session_token, token_hash)

    def new_registration_options(self, display_name: str, email: str, token: str,
                                 rp_id: str, rp_name: str, *, first_name: str | None = None,
                                 last_name: str | None = None, nickname: str | None = None) -> dict:
        return passkeys.new_registration_options(
            self, display_name, email, token, rp_id, rp_name,
            first_name=first_name, last_name=last_name, nickname=nickname,
        )

    def verify_new_registration(self, ceremony_id: str, credential: dict, rp_id: str, origin: str,
                                name: str = "Passkey") -> str:
        return passkeys.verify_new_registration(self, ceremony_id, credential, rp_id, origin, name)

    def issue_invitation(self, username: str) -> str:
        return registration.issue_invitation(self, username)

    def registration_options(self, username: str, token: str, rp_id: str, rp_name: str) -> dict:
        return passkeys.registration_options(self, username, token, rp_id, rp_name)

    def verify_registration(self, ceremony_id: str, credential: dict, rp_id: str, origin: str,
                            name: str = "Passkey") -> str:
        return passkeys.verify_registration(self, ceremony_id, credential, rp_id, origin, name)

    def security(self, token: str) -> dict:
        return {"passkeys": passkeys.list_passkeys(self, token), "password_set": passwords.is_set(self, token)}

    def rename_passkey(self, token: str, credential_id: str, name: str) -> None:
        passkeys.rename_passkey(self, token, credential_id, name)

    def add_passkey_options(self, token: str, rp_id: str, rp_name: str) -> dict:
        return passkeys.add_passkey_options(self, token, rp_id, rp_name)

    def verify_added_passkey(self, token: str, ceremony_id: str, credential: dict,
                            rp_id: str, origin: str, name: str) -> None:
        passkeys.verify_added_passkey(self, token, ceremony_id, credential, rp_id, origin, name)

    def set_password(self, token: str, password: str) -> None:
        passwords.set_password(self, token, password)

    def password_login(self, username: str, password: str, client: str = "") -> str:
        return passwords.login(self, username, password, client)

    def authentication_options(self, username: str, rp_id: str) -> dict:
        return passkeys.authentication_options(self, username, rp_id)

    def verify_authentication(self, ceremony_id: str, credential: dict, rp_id: str, origin: str) -> str:
        return passkeys.verify_authentication(self, ceremony_id, credential, rp_id, origin)

    def development_session(self) -> str:
        return sessions.development_session(self)

    def session_user(self, token: str) -> dict[str, str] | None:
        return sessions.session_user(self, token)

    def session_activity(self, token: str) -> bool:
        return sessions.activity(self, token)

    def session_account_id(self, token: str) -> str | None:
        return sessions.session_account_id(self, token)

    def logout(self, token: str) -> None:
        return sessions.logout(self, token)
