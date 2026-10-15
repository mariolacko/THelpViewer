"""Account errors, token hashing and shared profile validation."""

import hashlib
import re
import sqlite3

CEREMONY_LIFETIME = 300
EMAIL = re.compile(r"^[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+\.[^@\s\x00-\x1f\x7f]+$")


class AccountError(ValueError):
    """An account ceremony failed without exposing its private details."""


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def profile_names(first_name: str | None, last_name: str | None, nickname: str | None) -> tuple:
    names = tuple(value.strip() if value is not None else None for value in (first_name, last_name, nickname))
    if any(value is not None and (len(value) > 100 or any(ord(char) < 32 or ord(char) == 127 for char in value))
           for value in names):
        raise AccountError("Profile names must be at most 100 characters without control characters")
    return names


def profile_label(account: sqlite3.Row, names: tuple) -> str:
    first, last, nickname = (value if value is not None else account[field]
                             for field, value in zip(("first_name", "last_name", "nickname"), names))
    return (nickname or " ".join(value for value in (first, last) if value)
            or account["display_name"] or account["username"])[:100]
