"""Opt-in password authentication: salted scrypt, bounded work and throttling."""

from contextlib import closing
import hashlib
import hmac
import re
import secrets
import threading
import time
import unicodedata

from .common import AccountError, token_hash
from .sessions import new_session, owner

MIN_LENGTH, MAX_LENGTH = 15, 128
N, R, P = 2**15, 8, 3  # OWASP's 32 MiB scrypt profile.
_workers = threading.BoundedSemaphore(2)
_common = {"password", "password123", "password123456789", "123456789012345",
           "12345678901234567890", "qwertyuiopasdfgh", "letmein", "heslo", "heslo123",
           "admin", "administrator", "iloveyou", "changeme", "correcthorsebatterystaple"}


class PasswordRateLimit(AccountError):
    pass


def normalize(password: str) -> str:
    if not isinstance(password, str) or len(password) > MAX_LENGTH:
        raise AccountError(f"Password must contain {MIN_LENGTH}–{MAX_LENGTH} characters")
    value = unicodedata.normalize("NFC", password)
    if len(value) > MAX_LENGTH or any(unicodedata.category(char).startswith("C") for char in value):
        raise AccountError("Password contains unsupported control characters")
    return value


def validate(password: str, account) -> str:
    value = normalize(password)
    folded = value.casefold()
    if len(value) < MIN_LENGTH:
        raise AccountError(f"Use at least {MIN_LENGTH} characters; a longer passphrase is recommended")
    simple = re.sub(r"[^a-z0-9]", "", folded)
    if (folded.strip() in _common or len(set(folded)) < 4 or value.isspace()
            or re.fullmatch(r"(?:password|heslo|qwerty|admin|letmein)[0-9]*", simple)
            or folded in "0123456789" * 13 or folded in "123456789" * 15
            or folded in {account["username"].casefold(), account["email"].casefold(), account["display_name"].casefold()}):
        raise AccountError("Choose a less predictable password, not a common password or your account name")
    return value


def _derive(password: str, salt: bytes) -> bytes:
    if not _workers.acquire(blocking=False):
        raise PasswordRateLimit("Password service is busy; try again shortly")
    try:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=N, r=R, p=P, maxmem=64*1024*1024, dklen=32)
    finally:
        _workers.release()


def encode(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${N}${R}${P}${salt.hex()}${_derive(password, salt).hex()}"


def matches(password: str, encoded: str) -> bool:
    # A missing/invalid stored hash still costs one KDF, avoiding a fast path
    # that would disclose which public usernames have a password enabled.
    salt, expected, valid = bytes(16), bytes(32), False
    try:
        algorithm, n, r, p, raw_salt, raw_hash = encoded.split("$")
        if (algorithm, int(n), int(r), int(p)) == ("scrypt", N, R, P):
            salt, expected = bytes.fromhex(raw_salt), bytes.fromhex(raw_hash)
            valid = len(salt) == 16 and len(expected) == 32
    except (ValueError, TypeError):
        pass
    if not valid:
        salt, expected = bytes(16), bytes(32)
    return hmac.compare_digest(_derive(password, salt), expected) and valid


def is_set(store, token: str) -> bool:
    with closing(store._connect()) as connection:
        return bool(owner(connection, token)["password_hash"])


def set_password(store, token: str, password: str) -> None:
    with closing(store._connect()) as connection:
        account = owner(connection, token, recent_passkey=True)
        value = validate(password, account)
    encoded = encode(value)
    with closing(store._connect()) as connection, connection:
        account = owner(connection, token, recent_passkey=True)
        connection.execute("UPDATE accounts SET password_hash=? WHERE id=?", (encoded, account["id"]))
        connection.execute("DELETE FROM sessions WHERE account_id=? AND token_hash!=?", (account["id"], token_hash(token)))
        connection.execute("DELETE FROM ceremonies WHERE account_id=?", (account["id"],))
        connection.execute("DELETE FROM password_attempts WHERE key=?", (token_hash("account:" + account["id"]),))


def login(store, username: str, password: str, client: str) -> str:
    username = username.strip()
    value = normalize(password)
    now = int(time.time())
    with closing(store._connect()) as connection, connection:
        account = connection.execute(
            "SELECT id,password_hash FROM accounts WHERE (username=? OR email=? COLLATE NOCASE) AND active=1",
            (username, username),
        ).fetchone()
        key = token_hash("account:" + (account["id"] if account else username.casefold()))
        keys = [(key, 10)] + ([(token_hash("client:" + client), 120)] if client else [])
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM password_attempts WHERE started_at<=?", (now - 900,))
        for attempt_key, maximum in keys:
            row = connection.execute("SELECT attempts FROM password_attempts WHERE key=?", (attempt_key,)).fetchone()
            if row and row[0] >= maximum:
                raise PasswordRateLimit("Too many password attempts; try again in 15 minutes or use a Passkey")
        for attempt_key, _ in keys:
            connection.execute("INSERT INTO password_attempts(key,started_at,attempts) VALUES (?,?,1) "
                               "ON CONFLICT(key) DO UPDATE SET attempts=attempts+1", (attempt_key, now))
    encoded = account["password_hash"] if account else ""
    if not matches(value, encoded):
        raise AccountError("Email/username or password is incorrect")
    with closing(store._connect()) as connection, connection:
        current = connection.execute("SELECT 1 FROM accounts WHERE id=? AND active=1 AND password_hash=?",
                                     (account["id"], encoded)).fetchone()
        if not current:
            raise AccountError("Email/username or password is incorrect")
        connection.execute("DELETE FROM password_attempts WHERE key=?", (key,))
        return new_session(connection, account["id"], auth_method="password")
