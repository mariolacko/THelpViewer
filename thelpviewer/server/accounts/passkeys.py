"""WebAuthn challenges and credential verification for account enrollment/login."""

from __future__ import annotations

from typing import TYPE_CHECKING
from contextlib import closing
import base64
import json
import secrets
import sqlite3
import time
import uuid

from .common import AccountError, CEREMONY_LIFETIME, EMAIL, profile_names, token_hash
from .registration import account_for_invitation, registration_token
from .sessions import new_session, owner


if TYPE_CHECKING:
    from .store import AccountStore


def registration_options(store: AccountStore, username: str, token: str, rp_id: str, rp_name: str) -> dict:
    from webauthn import generate_registration_options
    from webauthn.helpers import options_to_json
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
        ResidentKeyRequirement, UserVerificationRequirement,
    )

    with closing(store._connect()) as connection, connection:
        account, digest = account_for_invitation(connection, username, token)
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


def consume_ceremony(connection: sqlite3.Connection, ceremony_id: str, kind: str):
    row = connection.execute(
        "DELETE FROM ceremonies WHERE id = ? AND kind = ? AND expires_at > ? "
        "RETURNING account_id, challenge, invitation_hash, session_hash",
        (ceremony_id, kind, int(time.time())),
    ).fetchone()
    if row is None:
        raise AccountError("Authentication request expired; please try again")
    connection.commit()
    return row


def verify_registration(store: AccountStore, ceremony_id: str, credential: dict, rp_id: str, origin: str,
                        name: str = "Passkey") -> str:
    from webauthn import verify_registration_response

    if len(json.dumps(credential)) > 16384:
        raise AccountError("Passkey response is too large")
    with closing(store._connect()) as connection, connection:
        ceremony = consume_ceremony(connection, ceremony_id, "register")
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
        insert_credential(connection, ceremony["account_id"], result, name)
        connection.execute("DELETE FROM invitations WHERE token_hash = ?", (ceremony["invitation_hash"],))
        return new_session(connection, ceremony["account_id"])


def authentication_options(store: AccountStore, username: str, rp_id: str) -> dict:
    from webauthn import generate_authentication_options
    from webauthn.helpers import options_to_json
    from webauthn.helpers.structs import PublicKeyCredentialDescriptor, UserVerificationRequirement

    with closing(store._connect()) as connection, connection:
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


def verify_authentication(store: AccountStore, ceremony_id: str, credential: dict, rp_id: str, origin: str) -> str:
    from webauthn import base64url_to_bytes, verify_authentication_response

    if len(json.dumps(credential)) > 16384:
        raise AccountError("Passkey response is too large")
    with closing(store._connect()) as connection, connection:
        ceremony = consume_ceremony(connection, ceremony_id, "authenticate")
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
            "UPDATE credentials SET sign_count = ?, device_type = ?, backed_up = ?, last_used_at=? WHERE credential_id = ?",
            (result.new_sign_count, str(result.credential_device_type),
             int(result.credential_backed_up), int(time.time()), credential_id),
        )
        return new_session(connection, ceremony["account_id"])


def new_registration_options(store: AccountStore, display_name: str, email: str, token: str,
                             rp_id: str, rp_name: str, *, first_name: str | None = None,
                             last_name: str | None = None, nickname: str | None = None) -> dict:
    from webauthn import generate_registration_options
    from webauthn.helpers import options_to_json
    from webauthn.helpers.structs import AuthenticatorSelectionCriteria, ResidentKeyRequirement, UserVerificationRequirement

    display_name = display_name.strip()
    email = email.strip().casefold()
    names = tuple(value or "" for value in profile_names(first_name, last_name, nickname))
    if not 1 <= len(display_name) <= 100 or not EMAIL.fullmatch(email) or len(email) > 254:
        raise AccountError("Enter a valid name and email address")
    display_name = names[2] or " ".join(value for value in names[:2] if value)[:100] or display_name
    with closing(store._connect()) as connection, connection:
        existing = connection.execute(
            "SELECT first_name, last_name, nickname FROM accounts WHERE email=? COLLATE NOCASE OR username=?",
            (email, email),
        ).fetchone()
        if existing:
            # An administrator-created account enrolls its own Passkey,
            # using the existing account-bound invitation, not a new account.
            result = store.registration_options(email, token.strip().upper(), rp_id, rp_name)
            return {**result, "enrollment": True, "profile": dict(existing)}
        registration = registration_token(connection, token)
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


def verify_new_registration(store: AccountStore, ceremony_id: str, credential: dict, rp_id: str, origin: str,
                            name: str = "Passkey") -> str:
    from webauthn import verify_registration_response

    if len(json.dumps(credential)) > 16384:
        raise AccountError("Passkey response is too large")
    with closing(store._connect()) as connection, connection:
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
            insert_credential(connection, pending["account_id"], result, name)
        except sqlite3.IntegrityError:
            raise AccountError("Account or Passkey is already registered") from None
        return new_session(connection, pending["account_id"])


def credential_name(name: str) -> str:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise AccountError("Passkey name must contain 1–80 characters without control characters")
    return name.strip()


def insert_credential(connection, account_id: str, result, name: str) -> None:
    name = credential_name(name)
    try:
        connection.execute(
            "INSERT INTO credentials(credential_id,account_id,public_key,sign_count,device_type,backed_up,name,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)", (result.credential_id, account_id, result.credential_public_key,
                result.sign_count, str(result.credential_device_type), int(result.credential_backed_up), name, int(time.time())),
        )
    except sqlite3.IntegrityError:
        raise AccountError("Passkey is already registered") from None


def list_passkeys(store: AccountStore, token: str) -> list[dict]:
    with closing(store._connect()) as connection:
        account = owner(connection, token)
        rows = connection.execute(
            "SELECT credential_id,name,created_at,last_used_at,backed_up FROM credentials "
            "WHERE account_id=? ORDER BY created_at,rowid", (account["id"],),
        ).fetchall()
    return [{"id": base64.urlsafe_b64encode(row["credential_id"]).decode().rstrip("="),
             "name": row["name"] or f"Passkey {index + 1}", "created_at": row["created_at"],
             "last_used_at": row["last_used_at"], "backed_up": bool(row["backed_up"])}
            for index, row in enumerate(rows)]


def rename_passkey(store: AccountStore, token: str, credential_id: str, name: str) -> None:
    from webauthn import base64url_to_bytes
    name = credential_name(name)
    try:
        ident = base64url_to_bytes(credential_id)
    except (ValueError, TypeError):
        raise AccountError("Passkey not found") from None
    with closing(store._connect()) as connection, connection:
        account = owner(connection, token)
        if connection.execute("UPDATE credentials SET name=? WHERE credential_id=? AND account_id=?",
                              (name, ident, account["id"])).rowcount != 1:
            raise AccountError("Passkey not found")


def add_passkey_options(store: AccountStore, token: str, rp_id: str, rp_name: str) -> dict:
    from webauthn import generate_registration_options
    from webauthn.helpers import options_to_json
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
        ResidentKeyRequirement, UserVerificationRequirement,
    )
    with closing(store._connect()) as connection, connection:
        account = owner(connection, token, recent_passkey=True)
        existing = connection.execute("SELECT credential_id FROM credentials WHERE account_id=?", (account["id"],)).fetchall()
        if len(existing) >= 20:
            raise AccountError("An account can have at most 20 Passkeys")
        options = generate_registration_options(
            rp_id=rp_id, rp_name=rp_name, user_id=bytes.fromhex(account["id"]),
            user_name=account["username"], user_display_name=account["display_name"],
            authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=bytes(row[0])) for row in existing],
        )
        ident = secrets.token_urlsafe(24)
        connection.execute("INSERT INTO ceremonies(id,account_id,kind,challenge,session_hash,expires_at) "
                           "VALUES (?,?,'add-passkey',?,?,?)", (ident, account["id"], options.challenge,
                            token_hash(token), int(time.time()) + CEREMONY_LIFETIME))
    return {"ceremony_id": ident, "options": json.loads(options_to_json(options))}


def verify_added_passkey(store: AccountStore, token: str, ceremony_id: str, credential: dict,
                         rp_id: str, origin: str, name: str) -> None:
    from webauthn import verify_registration_response
    name = credential_name(name)
    if len(json.dumps(credential)) > 16384:
        raise AccountError("Passkey response is too large")
    with closing(store._connect()) as connection, connection:
        account = owner(connection, token, recent_passkey=True)
        bound = connection.execute("SELECT 1 FROM ceremonies WHERE id=? AND account_id=? AND session_hash=?",
                                   (ceremony_id, account["id"], token_hash(token))).fetchone()
        if not bound:
            raise AccountError("Passkey request does not belong to this session")
        ceremony = consume_ceremony(connection, ceremony_id, "add-passkey")
        # Recheck after challenge consumption commits, including account disable/logout.
        connection.execute("BEGIN IMMEDIATE")
        owner(connection, token, recent_passkey=True)
        if connection.execute("SELECT COUNT(*) FROM credentials WHERE account_id=?", (account["id"],)).fetchone()[0] >= 20:
            raise AccountError("An account can have at most 20 Passkeys")
        try:
            result = verify_registration_response(credential=credential,
                expected_challenge=bytes(ceremony["challenge"]), expected_rp_id=rp_id,
                expected_origin=origin, require_user_verification=True)
        except Exception:
            raise AccountError("Passkey verification failed") from None
        insert_credential(connection, account["id"], result, name)
