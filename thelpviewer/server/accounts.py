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
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REGISTRATION_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


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
        columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
        if "email" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        if "role" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'member'")
            connection.execute(
                "UPDATE accounts SET role = 'admin' WHERE id = "
                "(SELECT id FROM accounts ORDER BY rowid LIMIT 1)"
            )
        registration_columns = {row[1] for row in connection.execute("PRAGMA table_info(registration_tokens)")}
        if "token_ciphertext" not in registration_columns:
            connection.execute("ALTER TABLE registration_tokens ADD COLUMN token_ciphertext BLOB")
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
                                 rp_id: str, rp_name: str) -> dict:
        from webauthn import generate_registration_options
        from webauthn.helpers import options_to_json
        from webauthn.helpers.structs import AuthenticatorSelectionCriteria, ResidentKeyRequirement, UserVerificationRequirement

        display_name = display_name.strip()
        email = email.strip().casefold()
        if not 2 <= len(display_name) <= 100 or not _EMAIL.fullmatch(email) or len(email) > 254:
            raise AccountError("Enter a valid name and email address")
        with closing(self._connect()) as connection, connection:
            registration = self._registration_token(connection, token)
            if connection.execute("SELECT 1 FROM accounts WHERE email = ? OR username = ?", (email, email)).fetchone():
                raise AccountError("Email address is already registered")
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
                "(id, account_id, token_hash, challenge, display_name, email, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ceremony_id, account_id, registration["token_hash"], options.challenge,
                 display_name, email, int(time.time()) + CEREMONY_LIFETIME),
            )
        return {"ceremony_id": ceremony_id, "options": json.loads(options_to_json(options))}

    def verify_new_registration(self, ceremony_id: str, credential: dict, rp_id: str, origin: str) -> str:
        from webauthn import verify_registration_response

        if len(json.dumps(credential)) > 16384:
            raise AccountError("Passkey response is too large")
        with closing(self._connect()) as connection, connection:
            pending = connection.execute(
                "DELETE FROM pending_registrations WHERE id = ? AND expires_at > ? "
                "RETURNING account_id, token_hash, challenge, display_name, email",
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
                    "INSERT INTO accounts(id, username, display_name, email, role) VALUES (?, ?, ?, ?, ?)",
                    (pending["account_id"], pending["email"], pending["display_name"],
                     pending["email"], "admin" if registration["bootstrap"] else "member"),
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
            try:
                connection.execute(
                    "INSERT INTO accounts(id, username, display_name, role) VALUES (?, ?, ?, ?)",
                    (account_id, username, (display_name.strip() or username)[:100],
                     "admin" if not connection.execute("SELECT 1 FROM accounts LIMIT 1").fetchone() else "member"),
                )
            except sqlite3.IntegrityError:
                raise AccountError("Account already exists") from None
        return self.issue_invitation(username)

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
                "SELECT 1 FROM invitations WHERE token_hash = ? AND account_id = ? AND expires_at > ?",
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
                "SELECT id FROM accounts WHERE username = ? AND active = 1", (username.strip(),)
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
                "SELECT a.username, a.display_name, a.email, a.role FROM sessions s "
                "JOIN accounts a ON a.id = s.account_id "
                "WHERE s.token_hash = ? AND s.expires_at > ? AND a.active = 1",
                (_token_hash(token), int(time.time())),
            ).fetchone()
        return None if row is None else {
            "username": row[0], "display_name": row[1], "email": row[2], "role": row[3],
        }

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
